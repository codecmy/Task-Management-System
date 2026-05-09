-- Smart Task Manager PostgreSQL Schema
-- Generated from SQLAlchemy models (User, Task)

CREATE TABLE public."user" (
    id SERIAL NOT NULL,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT user_pkey PRIMARY KEY (id),
    CONSTRAINT user_email_key UNIQUE (email)
);

CREATE INDEX ix_user_email ON public."user" (email);

CREATE TABLE public.task (
    id SERIAL NOT NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'todo',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    due_date DATE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    user_id INTEGER NOT NULL,
    CONSTRAINT task_pkey PRIMARY KEY (id),
    CONSTRAINT task_user_id_fkey FOREIGN KEY (user_id)
        REFERENCES public."user" (id) ON DELETE CASCADE
);
