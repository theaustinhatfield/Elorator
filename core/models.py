from django.conf import settings
from django.db import models


class Contest(models.Model):
    """A rating arena. The startup system uses a single arena (get_arena())."""
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_contests',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Submission(models.Model):
    """A YC-style startup application being rated."""
    SOURCE_HUMAN = 'human'
    SOURCE_AI = 'ai'
    SOURCE_CHOICES = [
        (SOURCE_HUMAN, 'Human founder'),
        (SOURCE_AI, 'AI agent'),
    ]
    OUTCOME_CHOICES = [
        ('successful', 'Funded by YC'),
        ('unsuccessful', 'Rejected by YC'),
        ('pending', 'Undecided'),
    ]

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='submissions')
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='submissions',
    )
    # Display / identity
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    company_name = models.CharField(max_length=255, blank=True)
    tagline = models.CharField(max_length=140, blank=True)
    # YC-style pitch fields
    pitch = models.TextField(blank=True, help_text='What the company will make (YC-style)')
    product = models.TextField(blank=True, help_text='What the company will make')
    whats_new = models.TextField(blank=True, help_text="What's new / substitutes")
    competitors = models.TextField(blank=True)
    insight = models.TextField(blank=True, help_text="What you understand that others don't")
    outcome = models.CharField(max_length=12, choices=OUTCOME_CHOICES, default='pending')
    batch = models.CharField(max_length=30, blank=True)
    # Provenance
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_HUMAN)
    model_name = models.CharField(
        max_length=100, blank=True,
        help_text='If source=ai: e.g. chatgpt, claude, muse-spark-1.3, glm-5.3',
    )
    founders_blurb = models.CharField(max_length=500, blank=True)
    is_public = models.BooleanField(
        default=True,
        help_text='False = private rating: rated vs anchors but hidden from leaderboard + fetch API',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.company_name or self.name or f'Submission {self.id}'

    @property
    def display_name(self):
        return self.company_name or self.name or f'#{self.id}'

    @property
    def rating_obj(self):
        try:
            return self.elo
        except EloRating.DoesNotExist:
            return None

    @property
    def rating_value(self):
        elo = self.rating_obj
        return elo.rating if elo else 1500


class EloRating(models.Model):
    """Denormalized Elo score per (contest, submission)."""
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='elo')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(default=1500)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    ties = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-rating']

    def __str__(self):
        return f'{self.submission.display_name}: {self.rating}'

    @property
    def decided(self):
        return self.wins + self.losses + self.ties


class Match(models.Model):
    """One pairwise verdict between two submissions."""
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='matches')
    submission_a = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='matches_as_a')
    submission_b = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='matches_as_b')
    winner = models.ForeignKey(
        Submission, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_won',
    )
    is_tie = models.BooleanField(default=False)
    judge = models.CharField(max_length=100, default='heuristic-v1')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'matches'

    def __str__(self):
        return f'{self.submission_a} vs {self.submission_b}'


class ContestField(models.Model):
    """Optional custom fields per contest (form builder)."""
    FIELD_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('link', 'Link'),
    ]
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    help_text = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.contest.title}: {self.label}'


class SubmissionValue(models.Model):
    """A value for a custom ContestField."""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='values')
    field = models.ForeignKey(ContestField, on_delete=models.CASCADE, related_name='values')
    value_text = models.TextField(blank=True)
    value_image = models.ImageField(upload_to='submission_images/', blank=True, null=True)

    def __str__(self):
        return f'{self.submission} / {self.field.label}'
