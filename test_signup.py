from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

try:
    res = supabase.auth.sign_up({'email': 'newuser11@example.com', 'password': 'password123'})
    print("SUCCESS:", res)
except Exception as e:
    print("ERROR:", str(e))
