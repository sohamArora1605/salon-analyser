create table if not exists source_datasets (
    id bigserial primary key,
    file_name text not null unique,
    domain text not null,
    target_table text not null,
    description text,
    row_count integer,
    loaded_at timestamptz default now()
);

create table if not exists appointments (
    id bigserial primary key,
    source_file text not null,
    client_code text,
    staff text,
    service_code text,
    appointment_date date,
    appointment_time time,
    time_int integer,
    created_at timestamptz default now()
);

create table if not exists cancellations (
    id bigserial primary key,
    source_file text not null,
    cancel_date date,
    client_code text,
    service_code text,
    service_price numeric(12, 2),
    staff text,
    booking_date date,
    canceled_by text,
    cancel_description text,
    days_before integer,
    created_at timestamptz default now()
);

create table if not exists no_shows (
    id bigserial primary key,
    source_file text not null,
    event_date date,
    client_code text,
    service_code text,
    staff text,
    created_at timestamptz default now()
);

create table if not exists products (
    id bigserial primary key,
    source_file text not null,
    is_active boolean,
    product_code text,
    description text,
    supplier text,
    brand text,
    category text,
    price numeric(12, 2),
    on_hand numeric(12, 2),
    minimum_stock numeric(12, 2),
    maximum_stock numeric(12, 2),
    cost numeric(12, 2),
    cogs numeric(12, 2),
    ytd numeric(12, 2),
    is_package boolean,
    created_at timestamptz default now()
);

create table if not exists services (
    id bigserial primary key,
    source_file text not null,
    is_active boolean,
    service_code text,
    description text,
    category text,
    price numeric(12, 2),
    cost numeric(12, 2),
    created_at timestamptz default now()
);

create table if not exists receipt_transactions (
    id bigserial primary key,
    source_file text not null,
    receipt_number text,
    transaction_date date,
    description text,
    client_code text,
    staff text,
    quantity numeric(12, 2),
    amount numeric(12, 2),
    gst numeric(12, 2),
    pst numeric(12, 2),
    created_at timestamptz default now()
);

create table if not exists ml_seed_events (
    id bigserial primary key,
    source_file text not null,
    payload jsonb not null,
    created_at timestamptz default now()
);

create table if not exists storage_uploads (
    id bigserial primary key,
    bucket text not null,
    object_key text not null,
    public_url text,
    uploaded_at timestamptz default now()
);

