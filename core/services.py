"""Elo engine + YC arena tournament scheduling.

Two flows share this code:
- Browser arena (humans vote pairwise)
- seed_yc_arena / API (heuristic-v1 AI judge, server keeps score)
"""
import math
import random
import re

K_FACTOR = 32
K_FACTOR_PROVISIONAL = 48  # first 10 decided matches per entry
PROVISIONAL_MATCHES = 10
MATCHES_PER_ENTRY = 8


def expected_score(rating_a, rating_b):
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))


def k_factor_for(decided_matches):
    return K_FACTOR_PROVISIONAL if decided_matches < PROVISIONAL_MATCHES else K_FACTOR


def update_elo(winner_rating, loser_rating, k=None):
    k = k or K_FACTOR
    expected_a = expected_score(winner_rating, loser_rating)
    expected_b = expected_score(loser_rating, winner_rating)
    new_winner = winner_rating + k * (1.0 - expected_a)
    new_loser = loser_rating + k * (0.0 - expected_b)
    return round(new_winner), round(new_loser)


def update_elo_tie(rating_a, rating_b, k=None):
    k = k or K_FACTOR
    expected_a = expected_score(rating_a, rating_b)
    expected_b = expected_score(rating_b, rating_a)
    new_a = rating_a + k * (0.5 - expected_a)
    new_b = rating_b + k * (0.5 - expected_b)
    return round(new_a), round(new_b)


def build_schedule(entry_ids, matches_per_entry=MATCHES_PER_ENTRY, seed=7):
    """Pairing schedule so every entry appears ~N times vs varied opponents.

    Greedy over shuffled pairs. Deterministic for a given id set + seed.
    """
    from itertools import combinations
    entry_ids = list(entry_ids)
    if len(entry_ids) < 2:
        return []
    rng = random.Random(f"{seed}:{sorted(entry_ids)}")
    pairs = list(combinations(sorted(entry_ids), 2))
    rng.shuffle(pairs)
    need = {oid: matches_per_entry for oid in entry_ids}
    schedule = []
    seen = set()
    for a, b in pairs:
        if need[a] > 0 and need[b] > 0:
            schedule.append((a, b))
            seen.add((a, b))
            need[a] -= 1
            need[b] -= 1
        if all(v <= 0 for v in need.values()):
            break
    from collections import Counter
    appearances = Counter(o for p in schedule for o in p)
    for a in [oid for oid, v in need.items() if v > 0]:
        while need[a] > 0:
            faced = {y if x == a else x for x, y in seen if a in (x, y)}
            cands = [oid for oid in entry_ids if oid != a and oid not in faced]
            if not cands:
                break
            b = min(cands, key=lambda oid: appearances[oid])
            schedule.append((a, b))
            seen.add((min(a, b), max(a, b)))
            appearances[a] += 1
            appearances[b] += 1
            need[a] -= 1
    return schedule


# ------------------------------------------------------------------ judging

BUZZWORD_PENALTIES = [
    'revolutionize', 'revolutionary', 'paradigm shift', 'disrupt everything',
    'unlock the power', 'game-changing', 'game changing', 'synergy',
    'world-changing', 'backed by vibes',
]
TRACTION_SIGNALS = [
    '$', '%', 'mrr', 'arr', 'users', 'revenue', 'paying', 'pilot',
    'customers', 'growth', 'traction', 'profit', 'retention',
]

_word_re = re.compile(r'[a-z0-9$%]+')


def _pitch_score(sub):
    """Heuristic-v1 quality score. Favors specific, traction-bearing pitches."""
    text = ' '.join([
        sub.tagline or '', sub.pitch or '', sub.product or '',
        sub.founders_blurb or '', sub.insight or '',
    ]).lower()
    score = 0.0
    # Specificity: longer, detailed pitches beat vague ones (diminishing).
    score += min(len(sub.pitch or ''), 1200) / 120.0
    score += min(len(sub.tagline or ''), 140) / 70.0
    for sig in TRACTION_SIGNALS:
        if sig in text:
            score += 1.2
    # Numbers ($41k, 200%, 1,500 users) signal real traction.
    score += min(len(re.findall(r'\d', text)), 12) * 0.35
    for buzz in BUZZWORD_PENALTIES:
        if buzz in text:
            score -= 3.0
    # Empty / missing pitch is the worst signal.
    if not (sub.pitch or sub.product):
        score -= 5.0
    return score


def heuristic_judge(sub_a, sub_b):
    """Deterministic heuristic-v1 judge. Returns (outcome, reason)."""
    sa, sb = _pitch_score(sub_a), _pitch_score(sub_b)
    diff = sa - sb
    if abs(diff) < 0.75:
        return 'tie', (
            f'heuristic-v1: both scored ~{sa:.1f} vs {sb:.1f}; '
            'no clear specificity/traction edge.'
        )
    if diff > 0:
        return 'a', (
            f'heuristic-v1: {sub_a.display_name} scores {sa:.1f} vs {sb:.1f} — '
            'more specific pitch with clearer customer, traction, or numbers.'
        )
    return 'b', (
        f'heuristic-v1: {sub_b.display_name} scores {sb:.1f} vs {sa:.1f} — '
        'more specific pitch with clearer customer, traction, or numbers.'
    )


def get_or_create_rating(submission, contest):
    from .models import EloRating
    rating, _ = EloRating.objects.get_or_create(
        submission=submission, defaults={'contest': contest},
    )
    # Keep contest pointer correct if arena was recreated.
    if rating.contest_id != contest.id:
        rating.contest = contest
        rating.save(update_fields=['contest'])
    return rating


def apply_startup_vote(match, outcome, reason='', judge='heuristic-v1'):
    """Record one pairwise verdict ('a' | 'b' | 'tie') and update EloRatings."""
    from django.db import transaction
    from .models import EloRating
    with transaction.atomic():
        match = type(match).objects.select_for_update().get(pk=match.pk)
        if match.winner_id is not None or match.is_tie:
            raise ValueError('match already decided')
        ra = get_or_create_rating(match.submission_a, match.contest)
        rb = get_or_create_rating(match.submission_b, match.contest)
        # Lock ratings for update.
        ra = EloRating.objects.select_for_update().get(pk=ra.pk)
        rb = EloRating.objects.select_for_update().get(pk=rb.pk)
        if outcome == 'tie':
            k = max(k_factor_for(ra.decided), k_factor_for(rb.decided))
            ra.rating, rb.rating = update_elo_tie(ra.rating, rb.rating, k=k)
            ra.ties += 1
            rb.ties += 1
            match.is_tie = True
            match.winner = None
        elif outcome in ('a', 'b'):
            winner_rating = ra if outcome == 'a' else rb
            loser_rating = rb if outcome == 'a' else ra
            k = max(k_factor_for(winner_rating.decided), k_factor_for(loser_rating.decided))
            new_w, new_l = update_elo(winner_rating.rating, loser_rating.rating, k=k)
            winner_rating.rating, loser_rating.rating = new_w, new_l
            winner_rating.wins += 1
            loser_rating.losses += 1
            match.winner = match.submission_a if outcome == 'a' else match.submission_b
        else:
            raise ValueError("outcome must be 'a', 'b' or 'tie'")
        match.reason = (reason or '')[:2000]
        match.judge = (judge or 'heuristic-v1')[:100]
        ra.save()
        rb.save()
        match.save()
    return match


def _judge_pair(sub_a, sub_b, judge='heuristic-v1'):
    if judge == 'heuristic-v1':
        return heuristic_judge(sub_a, sub_b)
    return heuristic_judge(sub_a, sub_b)


def run_tournament(subs, matches_per_entry=MATCHES_PER_ENTRY, judge='heuristic-v1'):
    """Run an AI-judged tournament over submissions. Returns list[Match]."""
    from .models import Match
    subs = list(subs)
    if len(subs) < 2:
        return []
    by_id = {s.id: s for s in subs}
    contest = subs[0].contest
    outcomes = []
    for a_id, b_id in build_schedule([s.id for s in subs], matches_per_entry=matches_per_entry):
        sub_a, sub_b = by_id[a_id], by_id[b_id]
        outcome, reason = _judge_pair(sub_a, sub_b, judge=judge)
        m = Match.objects.create(
            contest=contest, submission_a=sub_a, submission_b=sub_b, judge=judge,
        )
        apply_startup_vote(m, outcome, reason, judge=judge)
        m.refresh_from_db()
        outcomes.append(m)
    return outcomes


def run_full_round_robin(subs, judge='heuristic-v1'):
    """Every pair meets exactly once. Max info for a deterministic judge."""
    from itertools import combinations
    from .models import Match
    subs = list(subs)
    if len(subs) < 2:
        return []
    contest = subs[0].contest
    outcomes = []
    for sub_a, sub_b in combinations(subs, 2):
        outcome, reason = _judge_pair(sub_a, sub_b, judge=judge)
        m = Match.objects.create(
            contest=contest, submission_a=sub_a, submission_b=sub_b, judge=judge,
        )
        apply_startup_vote(m, outcome, reason, judge=judge)
        m.refresh_from_db()
        outcomes.append(m)
    return outcomes


def rate_new_submission(submission, anchors=None, placement_matches=10):
    """Rate a new submission with placement matches vs top anchors."""
    from .models import EloRating
    contest = submission.contest
    get_or_create_rating(submission, contest)
    if anchors is None:
        anchors = list(
            EloRating.objects.filter(contest=contest, submission__is_public=True)
            .exclude(submission=submission)
            .select_related('submission')
            .order_by('-rating')[:50]
        )
        anchors = [r.submission for r in anchors]
    anchors = [a for a in anchors if a.id != submission.id][:max(placement_matches * 2, 10)]
    if not anchors:
        return []
    import random as _random
    rng = _random.Random(submission.id)
    rng.shuffle(anchors)
    outcomes = []
    from .models import Match
    for opp in anchors[:placement_matches]:
        # Alternate sides so placement isn't side-biased.
        if len(outcomes) % 2 == 0:
            sub_a, sub_b, new_is_a = submission, opp, True
        else:
            sub_a, sub_b, new_is_a = opp, submission, False
        outcome, reason = heuristic_judge(sub_a, sub_b)
        m = Match.objects.create(
            contest=contest, submission_a=sub_a, submission_b=sub_b, judge='heuristic-v1',
        )
        apply_startup_vote(m, outcome, reason, judge='heuristic-v1')
        m.refresh_from_db()
        outcomes.append(m)
    return outcomes
