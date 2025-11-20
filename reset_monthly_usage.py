#!/usr/bin/env python3
"""Reset monthly invoice usage for all active subscriptions"""

import sys
sys.path.insert(0, '/var/www/invoice-app')

from database import get_connection

def reset_monthly_usage():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Reset all active subscriptions
    cursor.execute('''
        UPDATE subscriptions 
        SET invoices_used = 0 
        WHERE status IN ('active', 'canceling')
    ''')
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    print(f"[{__import__('datetime').datetime.now()}] Reset {affected} subscriptions")

if __name__ == "__main__":
    reset_monthly_usage()
