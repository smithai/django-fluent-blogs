from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import translation
from django.utils.module_loading import import_string
from django.views.generic.base import RedirectView
from django.views.generic.dates import DayArchiveView, MonthArchiveView, YearArchiveView, ArchiveIndexView
from django.views.generic.detail import DetailView, SingleObjectMixin
from fluent_blogs import appsettings
from fluent_blogs.models import get_entry_model, get_category_model
from fluent_blogs.models.query import get_date_range
from fluent_utils.django_compat import get_user_model
from fluent_utils.softdeps.fluent_pages import CurrentPageMixin, mixed_reverse
from parler.models import TranslatableModel, TranslationDoesNotExist
from parler.views import TranslatableSlugMixin


class BaseBlogMixin(CurrentPageMixin):
    context_object_name = None
    prefetch_translations = False
    view_url_name_paginated = None


    def get_queryset(self):
        # NOTE: This is also workaround, defining the queryset static somehow caused results to remain cached.
        qs = get_entry_model().objects.filter(parent_site=self.request.site)
        qs = qs.published()
        if self.prefetch_translations:
            qs = qs.prefetch_related('translations')
        return qs

    def get_language(self):
        """
        Return the language to display in this view.
        """
        return translation.get_language()  # Assumes that middleware has set this properly.

    def get_context_data(self, **kwargs):
        context = super(BaseBlogMixin, self).get_context_data(**kwargs)
        base_template = appsettings.FLUENT_BLOGS_BASE_TEMPLATE
        base_template_callback = appsettings.FLUENT_BLOGS_BASE_TEMPLATE_CALLBACK
        if base_template_callback:
            try:
                callback = import_string(base_template_callback)
                base_template = callback(self.request)
            except ImportError:
                pass
        context['FLUENT_BLOGS_BASE_TEMPLATE'] = base_template
        context['HAS_DJANGO_FLUENT_COMMENTS'] = 'fluent_comments' in settings.INSTALLED_APPS
        context['FLUENT_BLOGS_INCLUDE_STATIC_FILES'] = appsettings.FLUENT_BLOGS_INCLUDE_STATIC_FILES
        if self.context_object_name:
            context[self.context_object_name] = getattr(self, self.context_object_name)  # e.g. author, category, tag
        return context

    def get_view_url(self):
        # Support both use cases of the same view:
        if 'page' in self.kwargs:
            view_url_name = self.view_url_name_paginated
        else:
            view_url_name = self.view_url_name
        return mixed_reverse(view_url_name, args=self.args, kwargs=self.kwargs, current_page=self.get_current_page())



class BaseArchiveMixin(BaseBlogMixin):
    date_field = 'publication_date'
    month_format = '%m'
    allow_future = False
    paginate_by = 10

    def get_queryset(self):
        qs = super(BaseArchiveMixin, self).get_queryset()
        return qs.active_translations(self.get_language())  # NOTE: can't combine with other filters on translations__ relation.

    def get_template_names(self):
        names = super(BaseArchiveMixin, self).get_template_names()

        # Include the appname/model_suffix.html version for any customized model too.
        if not names[-1].startswith('fluent_blogs/entry'):
            names.append("fluent_blogs/entry{0}.html".format(self.template_name_suffix))

        return names


class BaseDetailMixin(TranslatableSlugMixin, BaseBlogMixin):
    # Only relevant at the detail page, e.g. for a language switch menu.
    prefetch_translations = appsettings.FLUENT_BLOGS_PREFETCH_TRANSLATIONS

    def get_queryset(self):
        qs = super(BaseDetailMixin, self).get_queryset()

        # Allow same slug in different dates
        # The available arguments depend on the FLUENT_BLOGS_ENTRY_LINK_STYLE setting.
        year = int(self.kwargs['year']) if 'year' in self.kwargs else None
        month = int(self.kwargs['month']) if 'month' in self.kwargs else None
        day = int(self.kwargs['day']) if 'day' in self.kwargs else None

        range = get_date_range(year, month, day)
        if range:
            qs = qs.filter(publication_date__range=range)

        return qs

    def get_object(self, queryset=None):
        if issubclass(get_entry_model(), TranslatableModel):
            # Filter by slug and language
            # Note that translation support is still optional,
            # even though the class inheritance includes it.
            return TranslatableSlugMixin.get_object(self, queryset)
        else:
            # Regular slug check, skip TranslatableSlugMixin
            return SingleObjectMixin.get_object(self, queryset)

    def get_language_choices(self):
        return appsettings.FLUENT_BLOGS_LANGUAGES.get_active_choices()

    def get_template_names(self):
        names = super(BaseDetailMixin, self).get_template_names()

        if not names[-1].startswith('fluent_blogs/entry'):
            names.append("fluent_blogs/entry{0}.html".format(self.template_name_suffix))

        return names


class EntryArchiveIndex(BaseArchiveMixin, ArchiveIndexView):
    """
    Archive index page.
    """
    view_url_name = 'entry_archive_index'
    view_url_name_paginated = 'entry_archive_index_paginated'
    template_name_suffix = '_archive_index'
    allow_empty = True


class EntryYearArchive(BaseArchiveMixin, YearArchiveView):
    view_url_name = 'entry_archive_year'
    make_object_list = True


class EntryMonthArchive(BaseArchiveMixin, MonthArchiveView):
    view_url_name = 'entry_archive_month'


class EntryDayArchive(BaseArchiveMixin, DayArchiveView):
    view_url_name = 'entry_archive_day'


class EntryDetail(BaseDetailMixin, DetailView):
    """
    Blog detail page.
    """
    view_url_name = 'entry_detail'


class EntryShortLink(SingleObjectMixin, RedirectView):
    permanent = False   # Allow changing the URL format

    def get_queryset(self):
        # NOTE: This is a workaround, defining the queryset static somehow caused results to remain cached.
        return get_entry_model().objects.published()

    def get_redirect_url(self, **kwargs):
        entry = self.get_object()
        try:
            return entry.get_absolute_url()
        except TranslationDoesNotExist as e:
            # Some entries may not have a language for the current site/subpath.
            raise Http404(str(e))



class EntryCategoryArchive(BaseArchiveMixin, ArchiveIndexView):
    """
    Archive based on tag.
    """
    view_url_name = 'entry_archive_category'
    view_url_name_paginated = 'entry_archive_category_paginated'
    template_name_suffix = '_archive_category'
    context_object_name = 'category'

    def get_queryset(self):
        self.category = get_object_or_404(get_category_model(), slug=self.kwargs['slug'])
        return super(EntryCategoryArchive, self).get_queryset().filter(categories=self.category)



class EntryAuthorArchive(BaseArchiveMixin, ArchiveIndexView):
    """
    Archive based on tag.
    """
    view_url_name = 'entry_archive_author'
    view_url_name_paginated = 'entry_archive_author_paginated'
    template_name_suffix = '_archive_author'
    context_object_name = 'author'

    def get_queryset(self):
        self.author = get_object_or_404(get_user_model(), pk=self.kwargs['author_id'])
        return super(EntryAuthorArchive, self).get_queryset().filter(author=self.author)


class EntryTagArchive(BaseArchiveMixin, ArchiveIndexView):
    """
    Archive based on tag.
    """
    view_url_name = 'entry_archive_tag'
    view_url_name_paginated = 'entry_archive_tag_paginated'
    template_name_suffix = '_archive_tag'
    context_object_name = 'tag'

    def get_queryset(self):
        from taggit.models import Tag  # django-taggit is optional, hence imported here.
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return super(EntryTagArchive, self).get_queryset().filter(tags=self.tag)
