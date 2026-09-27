"""Fresh start: wipe the arena and load the real YC applications fixture.

All ratings begin at 1500 with zero matches — no Elo tournament runs here.
Usage:
    python manage.py load_yc_fixture [--fixture core/fixtures/yc_apps.json]
"""
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Wipe arena data and load real YC applications at 1500 Elo, unrated.'

    def add_arguments(self, parser):
        parser.add_argument('--fixture', default='core/fixtures/yc_apps.json')

    def handle(self, *args, **opts):
        from core.models import EloRating, Submission
        from core.views import get_arena

        arena = get_arena()
        n_subs, _ = arena.submissions.all().delete()
        n_matches, _ = arena.matches.all().delete()
        self.stdout.write(f'wiped {n_subs} submissions, {n_matches} matches')

        with open(opts['fixture']) as f:
            apps = json.load(f)

        created = 0
        for app in apps:
            sub = Submission.objects.create(
                contest=arena,
                submitter=None,
                name=app['company'][:255],
                description=app['product'][:2000],
                company_name=app['company'][:255],
                tagline=app.get('tagline', '')[:140],
                pitch=app['product'],
                product=app['product'],
                whats_new=app.get('whats_new', ''),
                competitors=app.get('competitors', ''),
                insight=app.get('insight', ''),
                outcome=app.get('outcome', 'pending'),
                batch=app.get('batch', ''),
                source=Submission.SOURCE_HUMAN,
                model_name='',
                is_public=True,
            )
            EloRating.objects.create(submission=sub, contest=arena, rating=1500)
            created += 1

        from collections import Counter
        counts = Counter(a.get('outcome') for a in apps)
        total_matches = arena.matches.count()
        not_1500 = EloRating.objects.filter(contest=arena).exclude(rating=1500).count()
        self.stdout.write(
            f'loaded {created} apps {dict(counts)}, matches={total_matches}, non-1500={not_1500}'
        )
