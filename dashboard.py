#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung - Dashboard Module v3.1
Create visualizations and charts from processed invoices
"""

import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import pandas as pd

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Patch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("matplotlib not installed - charts disabled")


class DashboardGenerator:
    """Generate visual dashboards and charts"""
    
    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is required for dashboard generation")
        
        # Set style
        plt.style.use('dark_background')
        
        # Color scheme
        self.colors = {
            'primary': '#00d4ff',
            'success': '#00ff88',
            'warning': '#ffaa00',
            'danger': '#ff4444',
            'accent': '#9d00ff'
        }
    
    def generate_full_dashboard(self, results: List[Dict], stats: Dict) -> str:
        """Generate complete dashboard with multiple charts"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f"dashboard_{timestamp}.png"
        
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle('📊 Rechnungsverarbeitungs-Dashboard', 
                     fontsize=20, fontweight='bold', color=self.colors['primary'])
        
        # Layout: 2x3 grid
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Top Suppliers (Bar Chart)
        ax1 = fig.add_subplot(gs[0, :2])
        self._create_top_suppliers_chart(ax1, results)
        
        # 2. Amount Distribution (Pie Chart)
        ax2 = fig.add_subplot(gs[0, 2])
        self._create_amount_distribution(ax2, stats)
        
        # 3. Timeline (Line Chart)
        ax3 = fig.add_subplot(gs[1, :])
        self._create_timeline_chart(ax3, results)
        
        # 4. Statistics Box
        ax4 = fig.add_subplot(gs[2, 0])
        self._create_statistics_box(ax4, stats, len(results))
        
        # 5. Tax Breakdown (Bar Chart)
        ax5 = fig.add_subplot(gs[2, 1])
        self._create_tax_breakdown(ax5, stats)
        
        # 6. Validation Status (Donut Chart)
        ax6 = fig.add_subplot(gs[2, 2])
        self._create_validation_status(ax6, results)
        
        # Save
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
        plt.close()
        
        return str(output_file)
    
    def _create_top_suppliers_chart(self, ax, results: List[Dict]):
        """Top 10 suppliers by amount"""
        df = pd.DataFrame(results)
        
        if 'lieferant' in df.columns and 'betrag_brutto' in df.columns:
            top_suppliers = df.groupby('lieferant')['betrag_brutto'].sum().sort_values(ascending=False).head(10)
            
            bars = ax.barh(range(len(top_suppliers)), top_suppliers.values, 
                          color=self.colors['success'])
            ax.set_yticks(range(len(top_suppliers)))
            ax.set_yticklabels([s[:25] + '...' if len(s) > 25 else s for s in top_suppliers.index])
            ax.set_xlabel('Gesamtbetrag (€)', color='white')
            ax.set_title('🏆 Top 10 Lieferanten', fontweight='bold', color=self.colors['primary'])
            ax.grid(axis='x', alpha=0.3)
            
            # Add value labels
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2, 
                       f'{width:.0f}€', 
                       ha='left', va='center', color='white', fontsize=9)
    
    def _create_amount_distribution(self, ax, stats: Dict):
        """Amount distribution pie chart"""
        sizes = [stats['total_netto'], stats['total_mwst']]
        labels = ['Netto', 'MwSt.']
        colors = [self.colors['primary'], self.colors['accent']]
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('💰 Betragsverteilung', fontweight='bold', color=self.colors['primary'])
    
    def _create_timeline_chart(self, ax, results: List[Dict]):
        """Timeline of invoices"""
        df = pd.DataFrame(results)
        
        if 'datum' in df.columns and 'betrag_brutto' in df.columns:
            # Convert to datetime
            df['datum'] = pd.to_datetime(df['datum'], errors='coerce')
            df = df.dropna(subset=['datum'])
            
            # Group by date
            timeline = df.groupby('datum')['betrag_brutto'].sum().sort_index()
            
            if len(timeline) > 0:
                ax.plot(timeline.index, timeline.values, 
                       marker='o', linewidth=2, markersize=6, 
                       color=self.colors['success'])
                ax.fill_between(timeline.index, timeline.values, alpha=0.3, 
                               color=self.colors['success'])
                
                ax.set_xlabel('Datum', color='white')
                ax.set_ylabel('Betrag (€)', color='white')
                ax.set_title('📈 Zeitverlauf der Rechnungen', fontweight='bold', 
                           color=self.colors['primary'])
                ax.grid(alpha=0.3)
                
                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def _create_statistics_box(self, ax, stats: Dict, total_invoices: int):
        """Statistics text box"""
        ax.axis('off')
        
        stats_text = f"""
        📊 STATISTIKEN
        ═══════════════════
        
        Rechnungen:      {total_invoices}
        Gesamt Brutto:   {stats['total_brutto']:.2f}€
        Gesamt Netto:    {stats['total_netto']:.2f}€
        MwSt. Total:     {stats['total_mwst']:.2f}€
        Durchschnitt:    {stats['average_brutto']:.2f}€
        """
        
        ax.text(0.5, 0.5, stats_text, 
               horizontalalignment='center',
               verticalalignment='center',
               fontsize=11,
               color='white',
               family='monospace',
               bbox=dict(boxstyle='round', facecolor='#2b2b2b', alpha=0.8))
    
    def _create_tax_breakdown(self, ax, stats: Dict):
        """Tax breakdown bar chart"""
        categories = ['Netto', 'MwSt.', 'Brutto']
        amounts = [stats['total_netto'], stats['total_mwst'], stats['total_brutto']]
        colors_list = [self.colors['primary'], self.colors['accent'], self.colors['success']]
        
        bars = ax.bar(categories, amounts, color=colors_list)
        ax.set_ylabel('Betrag (€)', color='white')
        ax.set_title('💵 Steuer-Breakdown', fontweight='bold', color=self.colors['primary'])
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}€',
                   ha='center', va='bottom', color='white', fontweight='bold')
    
    def _create_validation_status(self, ax, results: List[Dict]):
        """Validation status donut chart"""
        valid_count = sum(1 for r in results if r.get('validation', {}).get('valid', True))
        invalid_count = len(results) - valid_count
        
        if invalid_count == 0:
            # All valid - show 100%
            sizes = [valid_count]
            labels = ['✅ Valid']
            colors_list = [self.colors['success']]
        else:
            sizes = [valid_count, invalid_count]
            labels = ['✅ Valid', '⚠️ Warnings']
            colors_list = [self.colors['success'], self.colors['warning']]
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.0f%%',
                                          colors=colors_list, startangle=90,
                                          wedgeprops=dict(width=0.5))
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('✅ Validierung', fontweight='bold', color=self.colors['primary'])
    
    def generate_monthly_report(self, results: List[Dict], month: str) -> str:
        """Generate monthly report chart"""
        
        output_file = self.output_dir / f"monthly_report_{month}.png"
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(f'📅 Monatsbericht {month}', 
                     fontsize=18, fontweight='bold', color=self.colors['primary'])
        
        df = pd.DataFrame(results)
        
        # Monthly trend
        if 'datum' in df.columns:
            df['datum'] = pd.to_datetime(df['datum'], errors='coerce')
            df['day'] = df['datum'].dt.day
            daily = df.groupby('day')['betrag_brutto'].sum()
            
            ax1.bar(daily.index, daily.values, color=self.colors['success'])
            ax1.set_xlabel('Tag des Monats', color='white')
            ax1.set_ylabel('Gesamtbetrag (€)', color='white')
            ax1.set_title('Tägliche Rechnungssummen', color=self.colors['primary'])
            ax1.grid(alpha=0.3)
        
        # Top suppliers
        if 'lieferant' in df.columns:
            top5 = df.groupby('lieferant')['betrag_brutto'].sum().nlargest(5)
            ax2.barh(range(len(top5)), top5.values, color=self.colors['primary'])
            ax2.set_yticks(range(len(top5)))
            ax2.set_yticklabels(top5.index)
            ax2.set_xlabel('Betrag (€)', color='white')
            ax2.set_title('Top 5 Lieferanten', color=self.colors['primary'])
            ax2.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
        plt.close()
        
        return str(output_file)


def generate_dashboard(results: List[Dict], stats: Dict, output_dir: str = "output/charts") -> str:
    """
    Convenience function to generate dashboard
    
    Usage:
        from dashboard import generate_dashboard
        chart_file = generate_dashboard(results, stats)
    """
    if not MATPLOTLIB_AVAILABLE:
        raise ImportError("Please install matplotlib: pip install matplotlib")
    
    generator = DashboardGenerator(output_dir)
    return generator.generate_full_dashboard(results, stats)
