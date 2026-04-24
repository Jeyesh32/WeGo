from django.db import models

from apps.common.models import TimestampedModel, UUIDPrimaryKeyModel


class Page(TimestampedModel):
    slug = models.SlugField(max_length=180, unique=True)
    title = models.CharField(max_length=255)
    excerpt = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    body_json = models.JSONField(default=dict, blank=True)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_pages")
    updated_by_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_pages")

    class Meta:
        db_table = "pages"


class BlogCategory(UUIDPrimaryKeyModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)

    class Meta:
        db_table = "blog_categories"


class BlogPost(TimestampedModel):
    category = models.ForeignKey("content.BlogCategory", on_delete=models.SET_NULL, null=True, blank=True)
    author_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    title = models.CharField(max_length=255)
    excerpt = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    body_json = models.JSONField(default=dict, blank=True)
    cover_image_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "blog_posts"
        indexes = [models.Index(fields=["category"]), models.Index(fields=["published_at"])]


class FAQ(UUIDPrimaryKeyModel):
    question = models.TextField()
    answer = models.TextField()
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faqs"


class Testimonial(UUIDPrimaryKeyModel):
    full_name = models.CharField(max_length=160)
    title = models.CharField(max_length=120, blank=True)
    company = models.CharField(max_length=120, blank=True)
    avatar_url = models.URLField(blank=True)
    rating = models.SmallIntegerField(null=True, blank=True)
    quote = models.TextField()
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "testimonials"


class PlatformSetting(models.Model):
    key = models.CharField(primary_key=True, max_length=120)
    value = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_settings"


class AuditLog(UUIDPrimaryKeyModel):
    actor_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=80)
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [models.Index(fields=["entity_type", "entity_id"]), models.Index(fields=["actor_user"])]
