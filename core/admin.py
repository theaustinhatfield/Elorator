from django.contrib import admin
from .models import Contest, ContestField, EloRating, Match, Submission, SubmissionValue


class EloRatingInline(admin.TabularInline):
    model = EloRating
    extra = 0
    readonly_fields = ['rating', 'wins', 'losses', 'ties', 'updated_at']


class MatchInline(admin.TabularInline):
    model = Match
    fk_name = 'contest'
    extra = 0
    readonly_fields = ['submission_a', 'submission_b', 'winner', 'is_tie', 'judge', 'created_at']


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at']
    inlines = [EloRatingInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contest', 'source', 'model_name', 'is_public', 'outcome', 'created_at']
    list_filter = ['source', 'is_public', 'outcome', 'contest']
    search_fields = ['company_name', 'tagline', 'pitch']


@admin.register(EloRating)
class EloRatingAdmin(admin.ModelAdmin):
    list_display = ['submission', 'contest', 'rating', 'wins', 'losses', 'ties']
    list_filter = ['contest']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['contest', 'submission_a', 'submission_b', 'winner', 'is_tie', 'judge', 'created_at']
    list_filter = ['is_tie', 'judge', 'contest']


@admin.register(ContestField)
class ContestFieldAdmin(admin.ModelAdmin):
    list_display = ['contest', 'label', 'field_type', 'required', 'order']


@admin.register(SubmissionValue)
class SubmissionValueAdmin(admin.ModelAdmin):
    list_display = ['submission', 'field']
