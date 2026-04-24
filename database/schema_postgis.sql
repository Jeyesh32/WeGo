BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_type') THEN
        CREATE TYPE user_role_type AS ENUM ('super_admin', 'admin', 'vendor', 'customer', 'staff');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_status_type') THEN
        CREATE TYPE account_status_type AS ENUM ('pending', 'active', 'suspended', 'deleted');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vendor_status_type') THEN
        CREATE TYPE vendor_status_type AS ENUM ('draft', 'pending_review', 'active', 'rejected', 'suspended');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'property_status_type') THEN
        CREATE TYPE property_status_type AS ENUM ('draft', 'pending_review', 'published', 'unpublished', 'archived');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'room_status_type') THEN
        CREATE TYPE room_status_type AS ENUM ('draft', 'published', 'maintenance', 'archived');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_status_type') THEN
        CREATE TYPE booking_status_type AS ENUM (
            'pending',
            'awaiting_payment',
            'confirmed',
            'checked_in',
            'checked_out',
            'completed',
            'cancelled',
            'refunded',
            'expired'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status_type') THEN
        CREATE TYPE payment_status_type AS ENUM ('pending', 'authorized', 'paid', 'failed', 'refunded', 'partially_refunded', 'voided');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_provider_type') THEN
        CREATE TYPE payment_provider_type AS ENUM (
            'cash',
            'stripe',
            'razorpay',
            'paypal',
            'paystack',
            'flutterwave',
            'manual',
            'other'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'media_owner_type') THEN
        CREATE TYPE media_owner_type AS ENUM ('platform', 'vendor', 'property', 'room', 'user', 'blog', 'page');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'device_platform_type') THEN
        CREATE TYPE device_platform_type AS ENUM ('android', 'ios', 'web');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role user_role_type NOT NULL DEFAULT 'customer',
    email CITEXT NOT NULL UNIQUE,
    phone VARCHAR(30),
    password_hash TEXT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(160),
    avatar_url TEXT,
    status account_status_type NOT NULL DEFAULT 'pending',
    email_verified_at TIMESTAMPTZ,
    phone_verified_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    label VARCHAR(80),
    line_1 VARCHAR(255) NOT NULL,
    line_2 VARCHAR(255),
    landmark VARCHAR(255),
    city VARCHAR(120),
    state VARCHAR(120),
    postal_code VARCHAR(30),
    country_code CHAR(2),
    location GEOGRAPHY(POINT, 4326),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_addresses_user_id ON user_addresses(user_id);
CREATE INDEX IF NOT EXISTS idx_user_addresses_location ON user_addresses USING GIST(location);

CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT,
    legal_name VARCHAR(200) NOT NULL,
    brand_name VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    support_email CITEXT,
    support_phone VARCHAR(30),
    description TEXT,
    logo_url TEXT,
    cover_image_url TEXT,
    commission_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    status vendor_status_type NOT NULL DEFAULT 'pending_review',
    rating_avg NUMERIC(3,2) NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vendors_owner_user_id ON vendors(owner_user_id);

CREATE TABLE IF NOT EXISTS vendor_staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    staff_role VARCHAR(40) NOT NULL DEFAULT 'operations',
    title VARCHAR(120),
    bio TEXT,
    permissions JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (vendor_id, user_id)
);

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL UNIQUE,
    description TEXT,
    billing_interval VARCHAR(20) NOT NULL CHECK (billing_interval IN ('monthly', 'yearly', 'lifetime')),
    price NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    trial_days INTEGER NOT NULL DEFAULT 0,
    max_properties INTEGER,
    max_rooms INTEGER,
    max_staff INTEGER,
    allows_featured_listing BOOLEAN NOT NULL DEFAULT FALSE,
    allows_promotions BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    feature_flags JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendor_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ,
    auto_renew BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'active', 'expired', 'cancelled')),
    external_reference VARCHAR(120),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vendor_subscriptions_vendor_id ON vendor_subscriptions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_subscriptions_plan_id ON vendor_subscriptions(plan_id);

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    property_name VARCHAR(180) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    property_type VARCHAR(80) NOT NULL DEFAULT 'hotel',
    short_description TEXT,
    description TEXT,
    address_line_1 VARCHAR(255) NOT NULL,
    address_line_2 VARCHAR(255),
    landmark VARCHAR(255),
    city VARCHAR(120) NOT NULL,
    state VARCHAR(120),
    postal_code VARCHAR(30),
    country_code CHAR(2) NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    base_check_in_minutes INTEGER NOT NULL DEFAULT 0,
    base_check_out_minutes INTEGER NOT NULL DEFAULT 0,
    minimum_booking_minutes INTEGER NOT NULL DEFAULT 120,
    maximum_booking_minutes INTEGER,
    instant_booking_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    status property_status_type NOT NULL DEFAULT 'draft',
    star_rating NUMERIC(2,1),
    rating_avg NUMERIC(3,2) NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    seo_title VARCHAR(255),
    seo_description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    search_document TSVECTOR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_properties_vendor_id ON properties(vendor_id);
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_properties_status_city ON properties(status, city);
CREATE INDEX IF NOT EXISTS idx_properties_search_document ON properties USING GIN(search_document);

CREATE TABLE IF NOT EXISTS property_amenities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL UNIQUE,
    icon_name VARCHAR(80),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS property_amenity_map (
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    amenity_id UUID NOT NULL REFERENCES property_amenities(id) ON DELETE CASCADE,
    PRIMARY KEY (property_id, amenity_id)
);

CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_name VARCHAR(180) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    room_code VARCHAR(60),
    description TEXT,
    max_adults INTEGER NOT NULL DEFAULT 2 CHECK (max_adults >= 1),
    max_children INTEGER NOT NULL DEFAULT 0 CHECK (max_children >= 0),
    max_guests INTEGER GENERATED ALWAYS AS (max_adults + max_children) STORED,
    size_sqft NUMERIC(10,2),
    bed_summary VARCHAR(120),
    bathroom_count NUMERIC(4,1),
    floor_label VARCHAR(40),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    status room_status_type NOT NULL DEFAULT 'draft',
    featured BOOLEAN NOT NULL DEFAULT FALSE,
    rating_avg NUMERIC(3,2) NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rooms_property_id ON rooms(property_id);
CREATE INDEX IF NOT EXISTS idx_rooms_status ON rooms(status);

CREATE TABLE IF NOT EXISTS room_amenities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL UNIQUE,
    icon_name VARCHAR(80),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS room_amenity_map (
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    amenity_id UUID NOT NULL REFERENCES room_amenities(id) ON DELETE CASCADE,
    PRIMARY KEY (room_id, amenity_id)
);

CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_type media_owner_type NOT NULL,
    owner_id UUID NOT NULL,
    storage_bucket VARCHAR(120),
    storage_path TEXT,
    public_url TEXT NOT NULL,
    alt_text VARCHAR(255),
    mime_type VARCHAR(120),
    width INTEGER,
    height INTEGER,
    file_size_bytes BIGINT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_assets_owner ON media_assets(owner_type, owner_id);

CREATE TABLE IF NOT EXISTS room_rate_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    tax_inclusive BOOLEAN NOT NULL DEFAULT FALSE,
    cancellation_policy TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_room_rate_plans_room_id ON room_rate_plans(room_id);

CREATE TABLE IF NOT EXISTS room_hourly_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_plan_id UUID NOT NULL REFERENCES room_rate_plans(id) ON DELETE CASCADE,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    compare_at_price NUMERIC(12,2),
    extra_guest_price NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rate_plan_id, duration_minutes)
);

CREATE INDEX IF NOT EXISTS idx_room_hourly_rates_rate_plan_id ON room_hourly_rates(rate_plan_id);

CREATE TABLE IF NOT EXISTS room_daily_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_plan_id UUID NOT NULL REFERENCES room_rate_plans(id) ON DELETE CASCADE,
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    base_price NUMERIC(12,2) NOT NULL CHECK (base_price >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rate_plan_id, weekday)
);

CREATE TABLE IF NOT EXISTS property_blackouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_property_blackouts_range ON property_blackouts(property_id, starts_at, ends_at);

CREATE TABLE IF NOT EXISTS room_blackouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_room_blackouts_range ON room_blackouts(room_id, starts_at, ends_at);

CREATE TABLE IF NOT EXISTS booking_guests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    email CITEXT,
    phone VARCHAR(30),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_number VARCHAR(40) NOT NULL UNIQUE,
    customer_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    rate_plan_id UUID REFERENCES room_rate_plans(id) ON DELETE SET NULL,
    hourly_rate_id UUID REFERENCES room_hourly_rates(id) ON DELETE SET NULL,
    staff_id UUID REFERENCES vendor_staff(id) ON DELETE SET NULL,
    status booking_status_type NOT NULL DEFAULT 'pending',
    source_channel VARCHAR(30) NOT NULL DEFAULT 'web' CHECK (source_channel IN ('web', 'android', 'admin', 'api')),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    booking_window TSTZRANGE GENERATED ALWAYS AS (tstzrange(starts_at, ends_at, '[)')) STORED,
    adult_count INTEGER NOT NULL DEFAULT 1 CHECK (adult_count >= 1),
    child_count INTEGER NOT NULL DEFAULT 0 CHECK (child_count >= 0),
    subtotal_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    service_fee_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    special_requests TEXT,
    cancellation_reason TEXT,
    cancelled_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    checked_in_at TIMESTAMPTZ,
    checked_out_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (ends_at > starts_at)
);

ALTER TABLE booking_guests
    ADD CONSTRAINT fk_booking_guests_booking
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_bookings_customer_user_id ON bookings(customer_user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_vendor_id ON bookings(vendor_id);
CREATE INDEX IF NOT EXISTS idx_bookings_property_id ON bookings(property_id);
CREATE INDEX IF NOT EXISTS idx_bookings_room_id ON bookings(room_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_time_window ON bookings USING GIST(booking_window);
CREATE INDEX IF NOT EXISTS idx_bookings_room_status ON bookings(room_id, status);

ALTER TABLE bookings
    ADD CONSTRAINT no_overlapping_active_bookings
    EXCLUDE USING GIST (
        room_id WITH =,
        booking_window WITH &&
    )
    WHERE (status IN ('confirmed', 'checked_in'));

CREATE TABLE IF NOT EXISTS booking_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    old_status booking_status_type,
    new_status booking_status_type NOT NULL,
    changed_by_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_booking_status_history_booking_id ON booking_status_history(booking_id);

CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    code VARCHAR(40) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('fixed', 'percent')),
    discount_value NUMERIC(12,2) NOT NULL CHECK (discount_value >= 0),
    max_discount_amount NUMERIC(12,2),
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    minimum_order_amount NUMERIC(12,2),
    usage_limit INTEGER,
    per_user_limit INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS booking_coupons (
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    coupon_id UUID NOT NULL REFERENCES coupons(id) ON DELETE RESTRICT,
    discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (booking_id, coupon_id)
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    payer_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    provider payment_provider_type NOT NULL,
    provider_reference VARCHAR(160),
    status payment_status_type NOT NULL DEFAULT 'pending',
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    currency_code CHAR(3) NOT NULL DEFAULT 'USD',
    paid_at TIMESTAMPTZ,
    failure_reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_booking_id ON payments(booking_id);
CREATE INDEX IF NOT EXISTS idx_payments_provider_reference ON payments(provider_reference);
CREATE INDEX IF NOT EXISTS idx_coupons_vendor_id ON coupons(vendor_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_coupons_platform_code
ON coupons (LOWER(code))
WHERE vendor_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_coupons_vendor_code
ON coupons (vendor_id, LOWER(code))
WHERE vendor_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    reason TEXT,
    provider_reference VARCHAR(160),
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID UNIQUE REFERENCES bookings(id) ON DELETE SET NULL,
    reviewer_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    vendor_id UUID REFERENCES vendors(id) ON DELETE CASCADE,
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    room_id UUID REFERENCES rooms(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(160),
    body TEXT,
    is_published BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_property_id ON reviews(property_id);
CREATE INDEX IF NOT EXISTS idx_reviews_room_id ON reviews(room_id);
CREATE INDEX IF NOT EXISTS idx_reviews_vendor_id ON reviews(vendor_id);

CREATE TABLE IF NOT EXISTS favorites (
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, room_id)
);

CREATE TABLE IF NOT EXISTS contact_inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    room_id UUID REFERENCES rooms(id) ON DELETE SET NULL,
    vendor_id UUID REFERENCES vendors(id) ON DELETE SET NULL,
    sender_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email CITEXT NOT NULL,
    phone VARCHAR(30),
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'read', 'resolved', 'spam')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    title VARCHAR(180) NOT NULL,
    body TEXT NOT NULL,
    notification_type VARCHAR(60) NOT NULL,
    deeplink TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id_read_at ON notifications(user_id, read_at);

CREATE TABLE IF NOT EXISTS device_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    platform device_platform_type NOT NULL,
    device_token TEXT NOT NULL UNIQUE,
    app_version VARCHAR(40),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens(user_id);

CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(180) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    excerpt TEXT,
    body_html TEXT,
    body_json JSONB,
    seo_title VARCHAR(255),
    seo_description TEXT,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_by_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    updated_by_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blog_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS blog_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES blog_categories(id) ON DELETE SET NULL,
    author_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    slug VARCHAR(180) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    excerpt TEXT,
    body_html TEXT,
    body_json JSONB,
    cover_image_url TEXT,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blog_posts_category_id ON blog_posts(category_id);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published_at ON blog_posts(published_at);

CREATE TABLE IF NOT EXISTS faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS testimonials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(160) NOT NULL,
    title VARCHAR(120),
    company VARCHAR(120),
    avatar_url TEXT,
    rating SMALLINT CHECK (rating BETWEEN 1 AND 5),
    quote TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_settings (
    key VARCHAR(120) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id UUID,
    action VARCHAR(80) NOT NULL,
    before_state JSONB,
    after_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_user_id ON audit_logs(actor_user_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION properties_search_document_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.search_document :=
        setweight(to_tsvector('simple', COALESCE(NEW.property_name, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.city, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.state, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.country_code, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.short_description, '')), 'D');
    RETURN NEW;
END;
$$;

CREATE OR REPLACE VIEW property_search_view AS
SELECT
    p.id,
    p.vendor_id,
    p.property_name,
    p.slug,
    p.property_type,
    p.city,
    p.state,
    p.country_code,
    p.location,
    ST_Y(p.location::geometry) AS latitude,
    ST_X(p.location::geometry) AS longitude,
    p.featured,
    p.status,
    p.star_rating,
    p.rating_avg,
    p.rating_count,
    p.currency_code,
    p.search_document,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'published') AS published_room_count,
    MIN(rhr.price) FILTER (WHERE rhr.is_active = TRUE) AS min_hourly_price
FROM properties p
LEFT JOIN rooms r
    ON r.property_id = p.id
LEFT JOIN room_rate_plans rrp
    ON rrp.room_id = r.id
    AND rrp.is_active = TRUE
LEFT JOIN room_hourly_rates rhr
    ON rhr.rate_plan_id = rrp.id
GROUP BY
    p.id,
    p.vendor_id,
    p.property_name,
    p.slug,
    p.property_type,
    p.city,
    p.state,
    p.country_code,
    p.location,
    p.featured,
    p.status,
    p.star_rating,
    p.rating_avg,
    p.rating_count,
    p.currency_code,
    p.search_document;

DROP TRIGGER IF EXISTS trg_app_users_updated_at ON app_users;
CREATE TRIGGER trg_app_users_updated_at
BEFORE UPDATE ON app_users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_user_addresses_updated_at ON user_addresses;
CREATE TRIGGER trg_user_addresses_updated_at
BEFORE UPDATE ON user_addresses
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_vendors_updated_at ON vendors;
CREATE TRIGGER trg_vendors_updated_at
BEFORE UPDATE ON vendors
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_vendor_staff_updated_at ON vendor_staff;
CREATE TRIGGER trg_vendor_staff_updated_at
BEFORE UPDATE ON vendor_staff
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_subscription_plans_updated_at ON subscription_plans;
CREATE TRIGGER trg_subscription_plans_updated_at
BEFORE UPDATE ON subscription_plans
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_vendor_subscriptions_updated_at ON vendor_subscriptions;
CREATE TRIGGER trg_vendor_subscriptions_updated_at
BEFORE UPDATE ON vendor_subscriptions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_properties_updated_at ON properties;
CREATE TRIGGER trg_properties_updated_at
BEFORE UPDATE ON properties
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_properties_search_document ON properties;
CREATE TRIGGER trg_properties_search_document
BEFORE INSERT OR UPDATE ON properties
FOR EACH ROW
EXECUTE FUNCTION properties_search_document_trigger();

DROP TRIGGER IF EXISTS trg_rooms_updated_at ON rooms;
CREATE TRIGGER trg_rooms_updated_at
BEFORE UPDATE ON rooms
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_room_rate_plans_updated_at ON room_rate_plans;
CREATE TRIGGER trg_room_rate_plans_updated_at
BEFORE UPDATE ON room_rate_plans
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_room_hourly_rates_updated_at ON room_hourly_rates;
CREATE TRIGGER trg_room_hourly_rates_updated_at
BEFORE UPDATE ON room_hourly_rates
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_room_daily_rates_updated_at ON room_daily_rates;
CREATE TRIGGER trg_room_daily_rates_updated_at
BEFORE UPDATE ON room_daily_rates
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_bookings_updated_at ON bookings;
CREATE TRIGGER trg_bookings_updated_at
BEFORE UPDATE ON bookings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_coupons_updated_at ON coupons;
CREATE TRIGGER trg_coupons_updated_at
BEFORE UPDATE ON coupons
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_payments_updated_at ON payments;
CREATE TRIGGER trg_payments_updated_at
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_reviews_updated_at ON reviews;
CREATE TRIGGER trg_reviews_updated_at
BEFORE UPDATE ON reviews
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_pages_updated_at ON pages;
CREATE TRIGGER trg_pages_updated_at
BEFORE UPDATE ON pages
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_blog_posts_updated_at ON blog_posts;
CREATE TRIGGER trg_blog_posts_updated_at
BEFORE UPDATE ON blog_posts
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

COMMIT;
