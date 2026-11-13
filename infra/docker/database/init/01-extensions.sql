-- Executado apenas na criação do volume. O esquema é criado pelo ETL (Alembic).
DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET timezone TO ''UTC''', current_database());
END
$$;
