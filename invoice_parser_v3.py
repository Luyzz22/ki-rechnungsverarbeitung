#!/usr/bin/env python3
"""
KI-Rechnungsverarbeitung v3.0 - CLI Version
Mit Parallel Processing, Validation & Multi-Export
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

from invoice_core import Config, InvoiceProcessor, get_pdf_files, calculate_statistics
from validation import validate_and_clean
from export import ExportManager, ReportGenerator

# Initialize
console = Console()
logger = logging.getLogger(__name__)


def print_header():
    """Print application header"""
    header = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║      🤖  KI-RECHNUNGSVERARBEITUNG v3.0  🤖             ║
    ║                                                          ║
    ║      Mit Parallel Processing & Validation               ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    console.print(header, style="bold cyan")


def process_batch_parallel(pdf_files, processor, max_workers=8):
    """Process PDFs in parallel"""
    results = []
    failed = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Verarbeite parallel...", total=len(pdf_files))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_pdf = {
                executor.submit(processor.process_invoice, pdf): pdf 
                for pdf in pdf_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_pdf):
                pdf = future_to_pdf[future]
                
                try:
                    data = future.result()
                    
                    if data:
                        # Validate and clean
                        cleaned, is_valid, errors = validate_and_clean(data)
                        
                        if is_valid:
                            results.append(cleaned)
                            console.print(
                                f"✅ [green]{pdf.name:<40}[/green] "
                                f"[cyan]{cleaned.get('lieferant', 'N/A'):<25}[/cyan] "
                                f"[yellow]{cleaned.get('betrag_brutto', 0):.2f}€[/yellow]"
                            )
                        else:
                            results.append(cleaned)  # Include with warnings
                            console.print(
                                f"⚠️  [yellow]{pdf.name:<40}[/yellow] "
                                f"Validierung: {len(errors)} Warnung(en)"
                            )
                    else:
                        failed.append(pdf.name)
                        console.print(f"❌ [red]{pdf.name:<40}[/red] Verarbeitung fehlgeschlagen")
                
                except Exception as e:
                    failed.append(pdf.name)
                    console.print(f"❌ [red]{pdf.name:<40}[/red] Error: {str(e)[:40]}")
                
                progress.advance(task)
    
    return results, failed


def process_batch_sequential(pdf_files, processor):
    """Process PDFs sequentially (fallback)"""
    results = []
    failed = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Verarbeite sequentiell...", total=len(pdf_files))
        
        for pdf in pdf_files:
            try:
                data = processor.process_invoice(pdf)
                
                if data:
                    cleaned, is_valid, errors = validate_and_clean(data)
                    
                    if is_valid:
                        results.append(cleaned)
                        console.print(
                            f"✅ [green]{pdf.name:<40}[/green] "
                            f"[cyan]{cleaned.get('lieferant', 'N/A'):<25}[/cyan] "
                            f"[yellow]{cleaned.get('betrag_brutto', 0):.2f}€[/yellow]"
                        )
                    else:
                        results.append(cleaned)
                        console.print(
                            f"⚠️  [yellow]{pdf.name:<40}[/yellow] "
                            f"Validierung: {len(errors)} Warnung(en)"
                        )
                else:
                    failed.append(pdf.name)
                    console.print(f"❌ [red]{pdf.name:<40}[/red] Verarbeitung fehlgeschlagen")
            
            except Exception as e:
                failed.append(pdf.name)
                console.print(f"❌ [red]{pdf.name:<40}[/red] Error: {str(e)[:40]}")
            
            progress.advance(task)
    
    return results, failed


def create_summary_table(results):
    """Create beautiful results table"""
    if not results:
        return None
    
    table = Table(
        title="📊 Top 10 Verarbeitete Rechnungen", 
        show_header=True, 
        header_style="bold magenta"
    )
    
    table.add_column("#", style="dim", width=4)
    table.add_column("Lieferant", style="cyan", width=30)
    table.add_column("Datum", style="yellow", width=12)
    table.add_column("Betrag", justify="right", style="green", width=12)
    table.add_column("Status", justify="center", width=8)
    
    # Sort by amount (descending) and take top 10
    sorted_results = sorted(
        [r for r in results if r.get('betrag_brutto')],
        key=lambda x: x.get('betrag_brutto', 0),
        reverse=True
    )[:10]
    
    for i, result in enumerate(sorted_results, 1):
        lieferant = result.get('lieferant', 'N/A')[:28]
        datum = result.get('datum', 'N/A')
        betrag = f"{result.get('betrag_brutto', 0):.2f}€"
        
        is_valid = result.get('validation', {}).get('valid', True)
        status = "✅" if is_valid else "⚠️"
        
        table.add_row(str(i), lieferant, datum, betrag, status)
    
    return table


def main():
    """Main program"""
    
    # Header
    print_header()
    
    try:
        # Load config
        config = Config()
        console.print("✅ [green]Konfiguration geladen[/green]\n")
        
        # Initialize processor
        processor = InvoiceProcessor(config)
        console.print("✅ [green]OpenAI API verbunden[/green]\n")
        
        # Get PDF files
        input_dir = config.get('processing.input_dir', 'test_rechnungen')
        pdf_files = get_pdf_files(input_dir)
        
        if not pdf_files:
            console.print(f"❌ [red]Keine PDFs in '{input_dir}' gefunden![/red]")
            console.print(f"→ [yellow]Kopiere PDFs in den Ordner und starte neu![/yellow]\n")
            return
        
        console.print(
            f"🚀 [bold cyan]Starte Verarbeitung von {len(pdf_files)} Rechnungen...[/bold cyan]\n"
        )
        
        # Check if parallel processing is enabled
        parallel = config.get('processing.parallel', True)
        max_workers = config.get('processing.max_workers', 8)
        
        if parallel and len(pdf_files) > 1:
            console.print(f"⚡ [cyan]Parallel-Modus aktiviert ({max_workers} Threads)[/cyan]\n")
            results, failed = process_batch_parallel(pdf_files, processor, max_workers)
        else:
            console.print("🔄 [cyan]Sequentieller Modus[/cyan]\n")
            results, failed = process_batch_sequential(pdf_files, processor)
        
        console.print("\n")
        
        # Display results
        if results:
            # Show table
            table = create_summary_table(results)
            if table:
                console.print(table)
            
            # Calculate statistics
            stats = calculate_statistics(results)
            
            # Generate summary
            summary = f"""
            ✅ [bold green]Verarbeitung abgeschlossen![/bold green]
            
            📊 Ergebnisse:
               • Erfolgreich: [cyan]{len(results)}/{len(pdf_files)}[/cyan]
               • Fehlgeschlagen: [red]{len(failed)}[/red]
               • Gesamt (Brutto): [green]{stats['total_brutto']:.2f}€[/green]
               • Gesamt (Netto): [yellow]{stats['total_netto']:.2f}€[/yellow]
               • MwSt. Total: [magenta]{stats['total_mwst']:.2f}€[/magenta]
               • Durchschnitt: [cyan]{stats['average_brutto']:.2f}€[/cyan]
            """
            
            console.print(Panel(summary, title="[bold]Zusammenfassung[/bold]", border_style="green"))
            
            # Export results
            console.print("\n💾 [cyan]Exportiere Daten...[/cyan]\n")
            
            export_config = {
                'formats': config.get('export.formats', ['xlsx']),
                'output_dir': config.get('export.output_dir', 'output'),
                'filename_prefix': config.get('export.filename_prefix', 'rechnungen'),
                'auto_open': config.get('export.auto_open', True)
            }
            
            exporter = ExportManager(export_config)
            exported_files = exporter.export_all(results, export_config['formats'])
            # DATEV Export (NEU!)
            if config.get('features.datev_export'):
                console.print("\n📤 [cyan]Erstelle DATEV-Export...[/cyan]")
                from datev_exporter import export_to_datev
                
                datev_config = {
                    'client_number': config.get('datev.client_number', '0'),
                    'consultant_number': config.get('datev.consultant_number', '0'),
                    'fiscal_year_start': config.get('datev.fiscal_year_start', '0101'),
                    'account_length': config.get('datev.account_length', 4)
                }
                
                try:
                    datev_file = export_to_datev(results, datev_config)
                    console.print(f"   ✅ [green]DATEV:[/green] {datev_file}")
                except Exception as e:
                    console.print(f"   ❌ [red]DATEV-Fehler:[/red] {e}")
            
            # Dashboard (NEU!)
            if config.get('features.dashboard'):
                console.print("\n📊 [cyan]Generiere Dashboard...[/cyan]")
                from dashboard import generate_dashboard
                
                try:
                    chart_file = generate_dashboard(results, stats)
                    console.print(f"   ✅ [green]DASHBOARD:[/green] {chart_file}")
                    
                    # Dashboard öffnen
                    import subprocess
                    subprocess.run(['open', chart_file], check=False)
                except Exception as e:
                    console.print(f"   ❌ [red]Dashboard-Fehler:[/red] {e}")
            for fmt, filepath in exported_files.items():
                console.print(f"   ✅ [green]{fmt.upper()}:[/green] {filepath}")
            
            # Generate and save report
            report_gen = ReportGenerator()
            report = report_gen.generate_summary_report(results, stats)
            report_path = report_gen.save_report(report, Path(export_config['output_dir']))
            console.print(f"   ✅ [green]REPORT:[/green] {report_path}")
            
            # Auto-open Excel if configured
            if export_config.get('auto_open') and 'xlsx' in exported_files:
                console.print("\n📂 [cyan]Öffne Excel...[/cyan]")
                exporter.open_file(exported_files['xlsx'])
            
            console.print("\n✨ [bold green]Fertig![/bold green]\n")
            
        else:
            console.print("❌ [red]Keine Rechnungen erfolgreich verarbeitet[/red]\n")
            
            if failed:
                console.print("❌ [red]Fehlgeschlagene PDFs:[/red]")
                for filename in failed:
                    console.print(f"   • {filename}")
                console.print()
    
    except Exception as e:
        console.print(f"\n❌ [bold red]Kritischer Fehler:[/bold red] {e}\n")
        logger.exception("Critical error in main()")


if __name__ == "__main__":
    main()
