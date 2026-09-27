"""Replay the 89-idea YC arena experiment.

Wipes the arena, loads the 59 real getintoyc.com applications (with actual
admit outcomes) + 30 Muse Spark 1.3 ideas, then replays the 671 individually
judged head-to-head admit verdicts to rebuild the Elo ratings.

Usage:
    python manage.py load_yc_arena [--fixture core/fixtures/yc_arena.json]
                                   [--judgments core/fixtures/judgments_671.json]
"""
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Load the 89-idea YC arena fixture and replay 671 judged verdicts.'

    def add_arguments(self, parser):
        parser.add_argument('--fixture', default='core/fixtures/yc_arena.json')
        parser.add_argument('--judgments', default='core/fixtures/judgments_671.json')

    def handle(self, *args, **opts):
        from core.models import EloRating, Match, Submission
        from core.services import apply_startup_vote
        from core.views import get_arena

        fx = json.load(open(opts['fixture']))
        verdicts = json.load(open(opts['judgments']))
        judge = fx.get('meta', {}).get('judge', 'human-yc-rank')

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
        by_name = {s.company_name: s for s in created.values()}
        n = 0
        for v in verdicts:
            sa, sb = by_name[v['a']], by_name[v['b']]
            m = Match.objects.create(contest=arena, submission_a=sa, submission_b=sb, judge=judge)
            apply_startup_vote(m, v['w'], 'YC-admit verdict: ' + v['r'], judge=judge)
            n += 1
        self.stdout.write(f'played {n} judged matches')

        board = (EloRating.objects.filter(contest=arena).select_related('submission')
                 .order_by('-rating')[:15])
        for i, r in enumerate(board, start=1):
            tag = f"{r.submission.source}:{r.submission.model_name}" if r.submission.source == 'ai' else 'human'
            self.stdout.write(f'{i:2d}. {r.rating:4d} [{tag}] {r.submission.company_name}')
