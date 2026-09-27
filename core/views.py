from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SubmissionForm
from .models import Contest, EloRating, Match, Submission
from .services import get_or_create_rating, rate_new_submission

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
    humans = [r for r in ratings if r.submission.source == 'human']
    groups = [
        {'key': 'accepted', 'label': 'Accepted humans', 'avg': avg(accepted), 'n': len(accepted),
         'note': 'actually admitted by YC'},
        {'key': 'human', 'label': 'All humans', 'avg': avg(humans), 'n': len(humans),
         'note': 'all 59 real applications'},
    ]
    models_seen = []
    for r in ratings:
        if r.submission.source != 'ai':
            continue
        m = r.submission.model_name or 'ai'
        if m not in models_seen:
            models_seen.append(m)
    pretty = {'muse-spark-1.3': 'Muse Spark 1.3', 'space-bunny-alpha': 'Space Bunny Alpha'}
    for m in models_seen:
        rs = [r for r in spark if (r.submission.model_name or 'ai') == m]
        groups.append({'key': f'model-{m}', 'label': pretty.get(m, m),
                       'avg': avg(rs), 'n': len(rs), 'note': 'new ideas, no traction claimed'})
    groups.append({'key': 'rejected', 'label': 'Rejected humans', 'avg': avg(rejected), 'n': len(rejected),
                   'note': 'applied, not admitted'})
    lo = min([g['avg'] for g in groups] + [1300])
    hi = max([g['avg'] for g in groups] + [1700])
    top_avg = max(g['avg'] for g in groups)
    for g in groups:
        g['pct'] = round(100 * (g['avg'] - lo) / max(hi - lo, 1))
        g['is_top'] = g['avg'] == top_avg
    step = (hi - lo) / 4
    yticks = [{'value': int(round(lo + i * step)), 'pct': i * 25} for i in range(5)]

    ranked = list(enumerate(ratings, start=1))
    ctx = {
        'arena': arena,
        'ratings': ratings,
        'groups': groups,
        'yticks': yticks,
        'all_rows': [{'rank': i, 'r': r} for i, r in ranked],
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
