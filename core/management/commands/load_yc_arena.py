"""Replay the 89-idea YC arena experiment.

Wipes the arena, loads the 59 real getintoyc.com applications (with actual
admit outcomes) + 30 Muse Spark 1.3 ideas, then replays the recorded
head-to-head admit judgments to rebuild the Elo ratings.

Usage:
    python manage.py load_yc_arena [--fixture core/fixtures/yc_arena.json]
"""
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Load the 89-idea YC arena fixture and replay recorded admit judgments.'

    def add_arguments(self, parser):
        parser.add_argument('--fixture', default='core/fixtures/yc_arena.json')
        parser.add_argument('--matches', type=int, default=None,
                            help='Matches per entry (default: fixture meta)')

    def handle(self, *args, **opts):
        from core.models import EloRating, Match, Submission
        from core.services import apply_startup_vote, build_schedule
        from core.views import get_arena

        fx = json.load(open(opts['fixture']))
        meta = fx.get('meta', {})
        ranks = {k: v['rank'] for k, v in fx['ranks'].items()}
        notes = {k: v['note'] for k, v in fx['ranks'].items()}
        ties = {tuple(sorted(t)) for t in fx.get('ties', [])}
        judge = meta.get('judge', 'human-yc-rank')
        mpe = opts['matches'] or meta.get('matches_per_entry', 8)
        seed = meta.get('seed', 7)

        arena = get_arena()
        n_subs, _ = arena.submissions.all().delete()
        arena.matches.all().delete()
        self.stdout.write(f'wiped {n_subs} submissions')

        created = {}
        for a in fx['apps']:
            pitch = a.get('product', '')
            if a.get('money'):
                pitch += '\n\nHow we make money: ' + a['money']
            if a.get('gtm'):
                pitch += '\n\nHow we get users: ' + a['gtm']
            s = Submission.objects.create(
                contest=arena, submitter=None,
                name=a['company'][:255], description=pitch[:2000],
                company_name=a['company'][:255], tagline=a.get('tagline', '')[:140],
                pitch=pitch, product=a.get('product', ''),
                whats_new=a.get('whats_new', ''), competitors=a.get('competitors', ''),
                insight=a.get('insight', ''), outcome=a.get('outcome', 'pending'),
                batch=a.get('batch', '')[:30], source=a.get('source', 'human'),
                model_name=a.get('model', '')[:100], is_public=True,
            )
            EloRating.objects.create(submission=s, contest=arena)
            created[a['company']] = s
        self.stdout.write(f"loaded {len(created)} ideas")

        by_id = {s.id: s for s in created.values()}
        sched = build_schedule(list(by_id), matches_per_entry=mpe, seed=seed)
        n = 0
        seen_ties = set()
        for a_id, b_id in sched:
            sa, sb = by_id[a_id], by_id[b_id]
            ca, cb = sa.company_name, sb.company_name
            key = tuple(sorted([ca, cb]))
            if key in ties:
                seen_ties.add(key)
                outcome, reason = 'tie', (
                    f"Admit-rank #{ranks[ca]} {ca} vs #{ranks[cb]} {cb}: "
                    f"near-identical ideas in the same space; genuine tie.")
            else:
                w, l = (ca, cb) if ranks[ca] < ranks[cb] else (cb, ca)
                outcome = 'a' if w == ca else 'b'
                reason = f"Admit-rank #{ranks[w]} {w} vs #{ranks[l]} {l}: {notes[w]}."
            m = Match.objects.create(contest=arena, submission_a=sa, submission_b=sb, judge=judge)
            apply_startup_vote(m, outcome, reason, judge=judge)
            n += 1
        for t in ties:
            if t not in seen_ties:
                sa, sb = created[t[0]], created[t[1]]
                m = Match.objects.create(contest=arena, submission_a=sa, submission_b=sb, judge=judge)
                apply_startup_vote(m, 'tie', (
                    f"Admit-rank #{ranks[t[0]]} {t[0]} vs #{ranks[t[1]]} {t[1]}: "
                    f"near-identical ideas in the same space; genuine tie."), judge=judge)
                n += 1
        for a_name, b_name, winner, reason in fx.get('rematches', []):
            sa, sb = created[a_name], created[b_name]
            m = Match.objects.create(contest=arena, submission_a=sa, submission_b=sb, judge=judge)
            apply_startup_vote(m, winner, reason, judge=judge)
            n += 1
        self.stdout.write(f'played {n} judged matches')

        board = (EloRating.objects.filter(contest=arena).select_related('submission')
                 .order_by('-rating')[:15])
        for i, r in enumerate(board, start=1):
            tag = f"{r.submission.source}:{r.submission.model_name}" if r.submission.source == 'ai' else 'human'
            self.stdout.write(f'{i:2d}. {r.rating:4d} [{tag}] {r.submission.company_name}')
