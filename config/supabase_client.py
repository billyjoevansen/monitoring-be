import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def get_supabase() -> Client:
    """Membuat koneksi ke Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_KEY harus diset di file .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_supabase_admin() -> Client:
    """Membuat koneksi ke Supabase dengan service role key (bypass RLS)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "SUPABASE_URL dan SUPABASE_SERVICE_ROLE_KEY harus diset di file .env"
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)