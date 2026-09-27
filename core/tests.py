from django.test import Client, TestCase

from .models import Contest, EloRating, Submission
from .services import heuristic_judge, run_full_round_robin, run_tournament
from .views import ARENA_TITLE, get_arena


def _mksub(arena, company, pitch, tagline='t', source='human', model='', public=True):
    s = Submission.objects.create(
        contest=arena, submitter=None, name=company, description=pitch[:2000],
        company_name=company, tagline=tagline, pitch=pitch,
        source=source, model_name=model, is_public=public,
    )
    EloRating.objects.create(submission=s, contest=arena)
    return s


class ArenaTest(TestCase):
    def setUp(self):
        self.arena = get_arena()
        self.assertEqual(self.arena.title, ARENA_TITLE)

    def test_heuristic_prefers_specific_over_vague(self):
        good = _mksub(self.arena, 'GoodCo',
                      'We charge dentists $249/mo, 9 clinics, $2k MRR, growing. ' * 5)
        vague = _mksub(self.arena, 'VagueCo',
                       'We will revolutionize synergy with game-changing vibes. ' * 2)
        outcome, reason = heuristic_judge(good, vague)
        self.assertEqual(outcome, 'a')
        self.assertIn('heuristic-v1', reason)

    def test_tournament_moves_elo(self):
        a = _mksub(self.arena, 'A', 'Revenue $10k MRR, 20 customers. ' * 10)
        b = _mksub(self.arena, 'B', 'Vibes. ' * 3)
        run_tournament([a, b], matches_per_entry=2)
        ra = EloRating.objects.get(submission=a)
        rb = EloRating.objects.get(submission=b)
        self.assertGreater(ra.rating, rb.rating)
        self.assertEqual(self.arena.matches.count(), 1)  # 2 subs = 1 pair max

    def test_round_robin_all_pairs(self):
        subs = [_mksub(self.arena, f'C{i}', f'Pitch {i} $1k MRR customers. ' * 5) for i in range(4)]
        outcomes = run_full_round_robin(subs)
        self.assertEqual(len(outcomes), 6)  # 4 choose 2

    def test_private_hidden_from_leaderboard_api(self):
        _mksub(self.arena, 'PubCo', 'Real traction $5k MRR. ' * 10, public=True)
        priv = _mksub(self.arena, 'PrivCo', 'Secret sauce. ' * 10, public=False)
        c = Client()
        r = c.get('/api/leaderboard/')
        self.assertEqual(r.status_code, 200)
        names = [x['company_name'] for x in r.json()['results']]
        self.assertIn('PubCo', names)
        self.assertNotIn('PrivCo', names)
        # detail page still viewable via unlisted link
        r2 = c.get(f'/startup/{priv.id}/')
        self.assertEqual(r2.status_code, 200)

    def test_submit_flow_places_new_entry(self):
        _mksub(self.arena, 'Anchor1', 'Revenue $10k MRR, 20 customers. ' * 10)
        _mksub(self.arena, 'Anchor2', 'Revenue $8k MRR, 15 customers. ' * 10)
        c = Client()
        r = c.post('/submit/', {
            'company_name': 'FlowCo',
            'tagline': 'Widgets for dentists',
            'pitch': 'We sell $249/mo software to 9 dental clinics, $2k MRR. ' * 4,
            'founders_blurb': 'Ex-dev + dentist',
            'is_public': 'on',
        })
        # redirect to detail on success
        self.assertEqual(r.status_code, 302)
        sub = Submission.objects.get(company_name='FlowCo')
        rating = EloRating.objects.get(submission=sub)
        self.assertNotEqual(rating.rating, 1500)  # placement matches moved it
        self.assertTrue(sub.is_public)
