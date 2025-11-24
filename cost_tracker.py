"""
API Cost Tracking & Analytics
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

# Pricing per 1M tokens (as of 2024)
PRICING = {
    'gpt-4o': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini': {'input': 0.150, 'output': 0.600},
    'claude-sonnet-4': {'input': 3.00, 'output': 15.00},
    'claude-haiku-3.5': {'input': 0.80, 'output': 4.00}
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Berechne Kosten basierend auf Token-Usage"""
    if model not in PRICING:
        return 0.0
    
    pricing = PRICING[model]
    input_cost = (input_tokens / 1_000_000) * pricing['input']
    output_cost = (output_tokens / 1_000_000) * pricing['output']
    
    return input_cost + output_cost

def track_api_cost(
    job_id: str,
    invoice_id: Optional[int],
    model: str,
    input_tokens: int,
    output_tokens: int,
    processing_time: float
):
    """Speichere API-Kosten"""
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO api_costs 
        (job_id, invoice_id, model, input_tokens, output_tokens, cost_usd, processing_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, invoice_id, model, input_tokens, output_tokens, cost, processing_time))
    
    conn.commit()
    conn.close()

def get_job_costs(job_id: str) -> Dict:
    """Hole Kosten für einen Job"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            COUNT(*) as api_calls,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            SUM(cost_usd) as total_cost,
            AVG(processing_time) as avg_processing_time,
            model
        FROM api_costs
        WHERE job_id = ?
        GROUP BY model
    ''', (job_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {'total_cost': 0, 'models': []}
    
    total_cost = sum(r['total_cost'] for r in rows)
    models = [dict(r) for r in rows]
    
    return {
        'total_cost': total_cost,
        'models': models,
        'total_api_calls': sum(m['api_calls'] for m in models)
    }

def get_monthly_costs() -> List[Dict]:
    """Hole monatliche Kosten"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', created_at) as month,
            COUNT(*) as api_calls,
            SUM(cost_usd) as total_cost,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens
        FROM api_costs
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def track_performance_metric(job_id: str, metric_name: str, value: float, unit: str):
    """Speichere Performance-Metrik"""
    conn = sqlite3.connect('invoices.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO performance_metrics (job_id, metric_name, metric_value, unit)
        VALUES (?, ?, ?, ?)
    ''', (job_id, metric_name, value, unit))
    
    conn.commit()
    conn.close()
