from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import SubmissionForm, VoteForm
from .models import Contest, EloRating, Match, Submission
from .services import apply_startup_vote, get_or_create_rating, rate_new_submission

ARENA_TITLE = 'YC Arena'
ARENA_DESCRIPTION = (
    'Pairwise Elo arena for YC-style startup pitches. '
    'Public submissions are free and listed; private ratings are hidden and paid.'
)


def get_arena():
    """The single startup arena, created on first use."""
    from django.contrib.auth.models import User
    creator = User.objects.filter(is_superuser=True).first() or User.objects.first()
    arena, _ = Contest.objects.get_or_create(
        title=ARENA_TITLE,
        defaults={'description': ARENA_DESCRIPTION, 'creator': creator},
    )
    return arena


def _public_ratings(arena):
    return (
        EloRating.objects.filter(contest=arena, submission__is_public=True)
        .select_related('submission')
        .order_by('-rating')
    )


def leaderboard(request):
    arena = get_arena()
    ratings = list(_public_ratings(arena))

    def avg(rs):
        return round(sum(r.rating for r in rs) / len(rs), 1) if rs else 1500.0

    accepted = [r for r in ratings if r.submission.source == 'human'
                and r.submission.outcome == 'successful']
    rejected = [r for r in ratings if r.submission.source == 'human'
                and r.submission.outcome != 'successful']
    spark = [r for r in ratings if r.submission.source == 'ai']
    groups = [
        {'key': 'accepted', 'label': 'Accepted humans', 'avg': avg(accepted), 'n': len(accepted),
         'note': 'actually admitted by YC'},
        {'key': 'spark', 'label': 'Muse Spark 1.3', 'avg': avg(spark), 'n': len(spark),
         'note': 'new ideas, no traction claimed'},
        {'key': 'rejected', 'label': 'Rejected humans', 'avg': avg(rejected), 'n': len(rejected),
         'note': 'applied, not admitted'},
    ]
    lo = min([g['avg'] for g in groups] + [1300])
    hi = max([g['avg'] for g in groups] + [1700])
    for g in groups:
        g['pct'] = round(100 * (g['avg'] - lo) / max(hi - lo, 1))

    ranked = list(enumerate(ratings, start=1))
    spark_rows = [{'rank': i, 'r': r} for i, r in ranked if r.submission.source == 'ai']
    ctx = {
        'arena': arena,
        'ratings': ratings,
        'groups': groups,
        'top_rows': [{'rank': i, 'r': r} for i, r in ranked[:30]],
        'spark_rows': spark_rows,
        'total_submissions': len(ratings),
        'total_matches': arena.matches.count(),
    }
    return render(request, 'core/leaderboard.html', ctx)


def submit(request):
    arena = get_arena()
    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            sub = Submission.objects.create(
                contest=arena,
                submitter=request.user if request.user.is_authenticated else None,
                name=cd['company_name'][:255],
                description=(cd['pitch'] or '')[:2000],
                company_name=cd['company_name'][:255],
                tagline=cd.get('tagline', '')[:140],
                pitch=cd['pitch'],
                product=cd.get('product', ''),
                whats_new=cd.get('whats_new', ''),
                competitors=cd.get('competitors', ''),
                insight=cd.get('insight', ''),
                founders_blurb=cd.get('founders_blurb', '')[:500],
                batch=cd.get('batch', '')[:30],
                source=Submission.SOURCE_HUMAN,
                model_name='',
                is_public=bool(cd.get('is_public', True)),
            )
            get_or_create_rating(sub, arena)
            outcomes = rate_new_submission(sub, placement_matches=10)
            if sub.is_public:
                messages.success(
                    request,
                    f'{sub.display_name} rated after {len(outcomes)} placement matches. '
                    'See where it landed.',
                )
                return redirect('detail', pk=sub.pk)
            messages.success(
                request,
                f'Private rating complete: {get_or_create_rating(sub, arena).rating} Elo '
                f'after {len(outcomes)} matches. Only you can see this page.',
            )
            return redirect('detail', pk=sub.pk)
    else:
        form = SubmissionForm()
    return render(request, 'core/submit.html', {'arena': arena, 'form': form})


def detail(request, pk):
    arena = get_arena()
    sub = get_object_or_404(Submission, pk=pk, contest=arena)
    # Private submissions: only the submitter (or anyone with the link, v1) can view.
    # v1 keeps it simple: unlisted but viewable with the link; hidden from leaderboard + API.
    rating = get_or_create_rating(sub, arena)
    public = list(_public_ratings(arena))
    rank = next((i + 1 for i, r in enumerate(public) if r.submission_id == sub.id), None)
    percentile = None
    if rank and public:
        percentile = round(100 * (len(public) - rank) / max(len(public) - 1, 1)) if len(public) > 1 else 100
    matches = (
        Match.objects.filter(contest=arena)
        .filter(Q(submission_a=sub) | Q(submission_b=sub))
        .select_related('submission_a', 'submission_b', 'winner')
        .order_by('-created_at')[:20]
    )
    return render(request, 'core/detail.html', {
        'arena': arena, 'sub': sub, 'rating': rating,
        'rank': rank, 'total': len(public), 'percentile': percentile,
        'matches': matches,
    })


def _pick_vote_pair(arena):
    import random
    ratings = list(_public_ratings(arena)[:60])
    if len(ratings) < 2:
        return None, None
    # Prefer close-rated pairs (informative votes), with some randomness.
    ratings_sorted = sorted(ratings, key=lambda r: r.rating)
    i = random.randrange(len(ratings_sorted) - 1)
    # 70%: neighbors; 30%: fully random.
    if random.random() < 0.7:
        ra, rb = ratings_sorted[i], ratings_sorted[i + 1]
    else:
        ra, rb = random.sample(ratings, 2)
    subs = [ra.submission, rb.submission]
    random.shuffle(subs)
    return subs[0], subs[1]


def vote(request):
    arena = get_arena()
    if request.method == 'POST':
        try:
            a_id = int(request.POST.get('a_id', 0))
            b_id = int(request.POST.get('b_id', 0))
        except (TypeError, ValueError):
            messages.error(request, 'Bad matchup. Try again.')
            return redirect('vote')
        sub_a = get_object_or_404(Submission, pk=a_id, contest=arena)
        sub_b = get_object_or_404(Submission, pk=b_id, contest=arena)
        form = VoteForm(request.POST)
        if form.is_valid():
            outcome = form.cleaned_data['winner']
            reason = form.cleaned_data.get('reason', '')
            judge = (
                request.user.username[:100]
                if request.user.is_authenticated else 'human'
            )
            m = Match.objects.create(
                contest=arena, submission_a=sub_a, submission_b=sub_b, judge=judge,
            )
            try:
                apply_startup_vote(m, outcome, reason, judge=judge)
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('vote')
            messages.success(request, 'Vote counted. Here is another.')
            return redirect('vote')
        # invalid form: re-render same pair
        return render(request, 'core/vote.html', {
            'arena': arena, 'sub_a': sub_a, 'sub_b': sub_b, 'form': form,
        })
    sub_a, sub_b = _pick_vote_pair(arena)
    if not sub_a:
        messages.info(request, 'Need at least 2 public submissions before voting. Submit one!')
        return redirect('submit')
    return render(request, 'core/vote.html', {
        'arena': arena, 'sub_a': sub_a, 'sub_b': sub_b, 'form': VoteForm(),
    })


# ------------------------------------------------------------------ fetch API

def api_leaderboard(request):
    """Public JSON leaderboard (private submissions excluded)."""
    arena = get_arena()
    ratings = _public_ratings(arena)[:100]
    return JsonResponse({
        'arena': arena.title,
        'count': len(ratings),
        'results': [{
            'id': r.submission.id,
            'company_name': r.submission.company_name,
            'tagline': r.submission.tagline,
            'rating': r.rating,
            'wins': r.wins, 'losses': r.losses, 'ties': r.ties,
            'batch': r.submission.batch,
            'outcome': r.submission.outcome,
        } for r in ratings],
    })


def api_submit(request):
    """Agent-facing rating endpoint: POST JSON, get Elo + percentile + reasons.

    Body: {company_name, tagline?, pitch/product, founders_blurb?, is_public?}
    Private (is_public=false) by default for API use; hidden from leaderboard.
    """
    import json
    if request.method != 'POST':
        return JsonResponse({'error': 'POST JSON to this endpoint'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON'}, status=400)
    company = str(data.get('company_name', '')).strip()[:255]
    pitch = str(data.get('pitch') or data.get('product') or '').strip()
    if not company or len(pitch) < 40:
        return JsonResponse(
            {'error': 'need company_name and pitch/product (40+ chars)'}, status=400)
    arena = get_arena()
    sub = Submission.objects.create(
        contest=arena, submitter=None,
        name=company, description=pitch[:2000], company_name=company,
        tagline=str(data.get('tagline', ''))[:140], pitch=pitch,
        product=str(data.get('product', '')),
        founders_blurb=str(data.get('founders_blurb', ''))[:500],
        whats_new=str(data.get('whats_new', '')),
        competitors=str(data.get('competitors', '')),
        insight=str(data.get('insight', '')),
        batch=str(data.get('batch', ''))[:30],
        source=Submission.SOURCE_AI if data.get('source') == 'ai' else Submission.SOURCE_HUMAN,
        model_name=str(data.get('model_name', ''))[:100],
        is_public=bool(data.get('is_public', False)),
    )
    rating = get_or_create_rating(sub, arena)
    outcomes = rate_new_submission(sub, placement_matches=10)
    public = list(_public_ratings(arena))
    rank = next((i + 1 for i, r in enumerate(public) if r.submission_id == sub.id), None)
    rating.refresh_from_db()
    return JsonResponse({
        'id': sub.id,
        'company_name': sub.company_name,
        'elo': rating.rating,
        'rank': rank, 'of': len(public),
        'is_public': sub.is_public,
        'placement_matches': len(outcomes),
        'matches': [{
            'vs': (m.submission_b.display_name if m.submission_a_id == sub.id
                   else m.submission_a.display_name),
            'outcome': ('win' if (m.winner_id == sub.id) else ('tie' if m.is_tie else 'loss')),
            'reason': m.reason,
        } for m in outcomes],
    })


@require_POST
def api_vote(request):
    """Human/agent vote: POST {a_id, b_id, winner: a|b|tie, reason?}."""
    import json
    try:
        data = json.loads(request.body or '{}') if request.content_type == 'application/json' else request.POST
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON'}, status=400)
    arena = get_arena()
    try:
        sub_a = Submission.objects.get(pk=int(data.get('a_id', 0)), contest=arena)
        sub_b = Submission.objects.get(pk=int(data.get('b_id', 0)), contest=arena)
    except (Submission.DoesNotExist, TypeError, ValueError):
        return JsonResponse({'error': 'unknown a_id/b_id'}, status=400)
    outcome = data.get('winner')
    if outcome not in ('a', 'b', 'tie'):
        return JsonResponse({'error': "winner must be 'a', 'b' or 'tie'"}, status=400)
    judge = str(data.get('judge', 'human'))[:100] or 'human'
    m = Match.objects.create(contest=arena, submission_a=sub_a, submission_b=sub_b, judge=judge)
    try:
        apply_startup_vote(m, outcome, str(data.get('reason', '')), judge=judge)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'ok': True, 'match_id': m.id})
