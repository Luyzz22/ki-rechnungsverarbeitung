"""
SBS Deutschland - Enterprise Settings Page
===========================================
Komplette get_settings_page() Funktion mit:
- Profil
- Unternehmen  
- Sicherheit (Passwort ändern)
- Benachrichtigungen (E-Mail, Slack mit Webhook, Wöchentlicher Report)
- API-Zugang
- 2FA
- Abmelden

INSTALLATION:
1. In pages_enterprise.py die bestehende get_settings_page() Funktion ersetzen
2. Imports prüfen (get_user_settings muss erweiterte Felder unterstützen)
"""

# ============================================================================
# DIESE FUNKTION ERSETZT get_settings_page() IN pages_enterprise.py
# ============================================================================

def get_settings_page(user_name: str = "User", user_email: str = "user@sbsdeutschland.com"):
    """Enterprise Settings Page mit Slack Webhook und Weekly Report"""
    
    # Settings laden
    settings = get_user_settings(user_email)
    
    # Plan für Feature-Gating laden
    try:
        from .usage_tracking import get_user_plan
        user_plan = get_user_plan(user_email)
        plan_id = user_plan.get("plan_id", "free")
    except:
        plan_id = "free"
    
    is_enterprise = plan_id == "enterprise"
    is_professional = plan_id in ["professional", "enterprise"]
    
    # API Key HTML
    if settings.get('api_key'):
        masked_key = f"{settings['api_key'][:12]}...{settings['api_key'][-6:]}"
        api_key_html = f'''<div id="apiKeyDisplay" style="background:#1e293b;border-radius:10px;padding:12px 16px;margin-top:12px;display:flex;align-items:center;gap:12px;">
          <code style="color:#22d3ee;word-break:break-all;flex:1;" id="apiKeyCode">{settings["api_key"]}</code>
          <button onclick="copyApiKey()" style="background:#334155;border:none;color:white;padding:8px 12px;border-radius:6px;cursor:pointer;" title="Kopieren">📋</button>
        </div>
        <button class="btn btn-danger" style="margin-top:12px;" onclick="revokeApiKey()">Widerrufen</button>'''
    else:
        api_key_html = '''<p style="color:var(--sbs-muted);margin-bottom:12px;">Noch kein API-Key generiert.</p>
        <button class="btn btn-primary" onclick="generateApiKey()" id="generateKeyBtn">API-Key generieren</button>
        <div id="newKeyDisplay" style="display:none;margin-top:12px;"></div>'''
    
    # Checkbox States
    email_checked = 'checked' if settings.get('notification_email', True) else ''
    slack_checked = 'checked' if settings.get('notification_slack') else ''
    slack_webhook = settings.get('slack_webhook_url') or ''
    weekly_checked = 'checked' if settings.get('weekly_report_enabled') else ''
    weekly_day = settings.get('weekly_report_day', 1)
    weekly_time = settings.get('weekly_report_time', '07:00')
    
    # Day Selection Options
    days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    day_options = ''.join([f'<option value="{i+1}" {"selected" if weekly_day == i+1 else ""}>{day}</option>' for i, day in enumerate(days)])
    
    # Feature Gating HTML
    if is_professional:
        slack_section_style = ''
        slack_disabled = ''
        slack_upgrade_html = ''
    else:
        slack_section_style = 'opacity: 0.6;'
        slack_disabled = 'disabled'
        slack_upgrade_html = '''
        <div style="margin-top:12px;padding:12px 16px;background:linear-gradient(135deg, #fef3c7, #fde68a);border-radius:10px;border:1px solid #fcd34d;">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:1.2rem;">🔒</span>
            <div>
              <strong style="color:#92400e;">Professional Feature</strong>
              <p style="margin:4px 0 0;font-size:0.85rem;color:#a16207;">Slack Integration ist ab dem Professional Plan verfügbar.</p>
            </div>
            <a href="/billing" class="btn btn-primary" style="margin-left:auto;padding:8px 16px;font-size:0.85rem;">Upgrade →</a>
          </div>
        </div>'''
    
    if is_enterprise:
        weekly_section_style = ''
        weekly_disabled = ''
        weekly_upgrade_html = ''
    else:
        weekly_section_style = 'opacity: 0.6;'
        weekly_disabled = 'disabled'
        weekly_upgrade_html = '''
        <div style="margin-top:12px;padding:12px 16px;background:linear-gradient(135deg, #fef3c7, #fde68a);border-radius:10px;border:1px solid #fcd34d;">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="font-size:1.2rem;">🔒</span>
            <div>
              <strong style="color:#92400e;">Enterprise Feature</strong>
              <p style="margin:4px 0 0;font-size:0.85rem;color:#a16207;">Wöchentliche Reports sind nur im Enterprise Plan verfügbar.</p>
            </div>
            <a href="/billing" class="btn btn-primary" style="margin-left:auto;padding:8px 16px;font-size:0.85rem;">Upgrade →</a>
          </div>
        </div>'''
    
    # Slack Config Display
    slack_config_display = 'block' if slack_checked and is_professional else 'none'
    weekly_config_display = 'block' if weekly_checked and is_enterprise else 'none'
    
    content = f"""
<style>
.toggle-switch {{ position: relative; display: inline-block; width: 52px; height: 28px; flex-shrink: 0; }}
.toggle-switch input {{ opacity: 0; width: 0; height: 0; }}
.toggle-slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; border-radius: 28px; transition: .3s; }}
.toggle-slider:before {{ position: absolute; content: ""; height: 22px; width: 22px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: .3s; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
input:checked + .toggle-slider {{ background-color: #22c55e; }}
input:checked + .toggle-slider:before {{ transform: translateX(24px); }}
input:disabled + .toggle-slider {{ opacity: 0.5; cursor: not-allowed; }}
.toast {{ position:fixed; bottom:24px; right:24px; background:#1e293b; color:white; padding:16px 24px; border-radius:12px; display:none; z-index:2000; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }}
.toast.show {{ display:flex; align-items:center; gap:12px; animation: slideIn 0.3s ease; }}
@keyframes slideIn {{ from {{ transform:translateY(20px); opacity:0; }} to {{ transform:translateY(0); opacity:1; }} }}
.badge-pro {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 3px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; margin-left: 10px; text-transform: uppercase; }}
.badge-enterprise {{ background: linear-gradient(135deg, #FFB900, #f59e0b); color: #1e293b; padding: 3px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; margin-left: 10px; text-transform: uppercase; }}
.settings-section {{ border-bottom: 1px solid #e2e8f0; }}
.settings-section:last-child {{ border-bottom: none; }}
.settings-row {{ display: flex; justify-content: space-between; align-items: flex-start; padding: 20px 24px; }}
.settings-info {{ flex: 1; padding-right: 24px; }}
.settings-info strong {{ display: flex; align-items: center; font-size: 0.95rem; color: #1e293b; }}
.settings-info p {{ margin: 4px 0 0; font-size: 0.85rem; color: #64748b; }}
.settings-config {{ margin-top: 16px; padding: 16px; background: #f8fafc; border-radius: 12px; }}
.input-group {{ display: flex; gap: 8px; margin-bottom: 12px; }}
.input-group input {{ flex: 1; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.9rem; }}
.input-group input:disabled {{ background: #f1f5f9; cursor: not-allowed; }}
.form-row {{ display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; }}
.form-row .form-field {{ display: flex; flex-direction: column; gap: 6px; }}
.form-row .form-field label {{ font-size: 0.8rem; color: #64748b; font-weight: 500; }}
.form-row .form-field select, .form-row .form-field input {{ padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.9rem; }}
.form-row .form-field select:disabled, .form-row .form-field input:disabled {{ background: #f1f5f9; cursor: not-allowed; }}
</style>

<div class="hero">
  <div class="container">
    <div class="hero-badge"><span class="dot"></span> EINSTELLUNGEN</div>
    <h1>⚙️ Einstellungen</h1>
    <p>Verwalten Sie Ihr Konto, Benachrichtigungen und Integrationen.</p>
  </div>
</div>

<div class="page-container">
  
  <!-- Sidebar Navigation -->
  <div class="settings-nav" style="display:flex;gap:32px;">
    <div class="settings-sidebar" style="width:240px;flex-shrink:0;">
      <div class="content-card" style="position:sticky;top:100px;">
        <div class="content-card-body" style="padding:16px;">
          <div style="font-size:0.75rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;padding:8px 12px;">Einstellungen</div>
          <a href="#profile" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#1e293b;text-decoration:none;transition:all 0.15s;">👤 Profil</a>
          <a href="#company" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#1e293b;text-decoration:none;transition:all 0.15s;">🏢 Unternehmen</a>
          <a href="#security" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#1e293b;text-decoration:none;transition:all 0.15s;">🔐 Sicherheit</a>
          <a href="#notifications" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#003856;background:rgba(0,56,86,0.08);text-decoration:none;font-weight:500;">🔔 Benachrichtigungen</a>
          <a href="#api" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#1e293b;text-decoration:none;transition:all 0.15s;">🔑 API-Zugang</a>
          <a href="#subscription" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#1e293b;text-decoration:none;transition:all 0.15s;">💳 Abonnement</a>
          <a href="#products" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#1e293b;text-decoration:none;transition:all 0.15s;">📦 Produkte</a>
          <div style="border-top:1px solid #e2e8f0;margin:12px 0;"></div>
          <a href="/logout" class="settings-nav-item" style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;color:#dc2626;text-decoration:none;transition:all 0.15s;">🚪 Abmelden</a>
        </div>
      </div>
    </div>
    
    <!-- Main Content -->
    <div class="settings-content" style="flex:1;min-width:0;">
    
      <!-- Profil Card -->
      <div class="content-card" id="profile" style="margin-bottom:24px;">
        <div class="content-card-header" style="display:flex;align-items:center;gap:12px;">
          <div style="width:44px;height:44px;background:linear-gradient(135deg,#003856,#00507a);border-radius:12px;display:flex;align-items:center;justify-content:center;">
            <span style="font-size:1.3rem;">👤</span>
          </div>
          <div>
            <h3 class="content-card-title" style="margin:0;">Profil</h3>
            <p style="margin:2px 0 0;font-size:0.85rem;color:#64748b;">Ihre persönlichen Informationen</p>
          </div>
        </div>
        <div class="content-card-body">
          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">Name</label>
            <input type="text" class="form-input" value="{user_name}" id="profileName">
          </div>
          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">E-Mail</label>
            <input type="email" class="form-input" value="{user_email}" disabled style="background:#f8fafc;">
          </div>
          <button class="btn btn-primary" onclick="saveProfile()">💾 Speichern</button>
        </div>
      </div>
      
      <!-- Benachrichtigungen Card - ERWEITERT -->
      <div class="content-card" id="notifications" style="margin-bottom:24px;">
        <div class="content-card-header" style="display:flex;align-items:center;gap:12px;">
          <div style="width:44px;height:44px;background:linear-gradient(135deg,#f59e0b,#fbbf24);border-radius:12px;display:flex;align-items:center;justify-content:center;">
            <span style="font-size:1.3rem;">🔔</span>
          </div>
          <div>
            <h3 class="content-card-title" style="margin:0;">Benachrichtigungen</h3>
            <p style="margin:2px 0 0;font-size:0.85rem;color:#64748b;">Konfigurieren Sie wie Sie informiert werden</p>
          </div>
        </div>
        <div class="content-card-body" style="padding:0;">
          
          <!-- E-Mail Benachrichtigungen -->
          <div class="settings-section">
            <div class="settings-row">
              <div class="settings-info">
                <strong>📧 E-Mail Benachrichtigungen</strong>
                <p>Erhalten Sie Updates zu Ihren Dokumenten per E-Mail</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" id="emailToggle" {email_checked} onchange="saveNotifications('email', this.checked)">
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
          
          <!-- Slack Integration -->
          <div class="settings-section" style="{slack_section_style}">
            <div class="settings-row">
              <div class="settings-info">
                <strong>
                  💬 Slack Integration
                  <span class="badge-pro">PRO+</span>
                </strong>
                <p>Benachrichtigungen an Ihren Slack Workspace senden</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" id="slackToggle" {slack_checked} onchange="toggleSlackConfig(this.checked)" {slack_disabled}>
                <span class="toggle-slider"></span>
              </label>
            </div>
            
            <!-- Slack Konfiguration -->
            <div id="slackConfig" style="display:{slack_config_display};padding:0 24px 20px;">
              <div class="settings-config">
                <label style="display:block;font-size:0.85rem;color:#475569;margin-bottom:8px;font-weight:500;">Webhook URL</label>
                <div class="input-group">
                  <input type="text" id="slackWebhook" value="{slack_webhook}" 
                         placeholder="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX" 
                         {slack_disabled}>
                  <button class="btn btn-secondary" onclick="testSlackWebhook()" id="testSlackBtn" {slack_disabled}>🧪 Testen</button>
                  <button class="btn btn-primary" onclick="saveSlackWebhook()" {slack_disabled}>💾 Speichern</button>
                </div>
                <p style="margin:0;font-size:0.8rem;color:#64748b;">
                  <a href="https://api.slack.com/messaging/webhooks" target="_blank" style="color:#003856;">
                    📖 Anleitung: Slack Webhook URL erstellen →
                  </a>
                </p>
              </div>
            </div>
            {slack_upgrade_html}
          </div>
          
          <!-- Wöchentlicher Report -->
          <div class="settings-section" style="{weekly_section_style}">
            <div class="settings-row">
              <div class="settings-info">
                <strong>
                  📊 Wöchentlicher Report
                  <span class="badge-enterprise">ENTERPRISE</span>
                </strong>
                <p>Zusammenfassung Ihrer Aktivitäten jeden Montag</p>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" id="weeklyToggle" {weekly_checked} onchange="toggleWeeklyConfig(this.checked)" {weekly_disabled}>
                <span class="toggle-slider"></span>
              </label>
            </div>
            
            <!-- Weekly Report Konfiguration -->
            <div id="weeklyConfig" style="display:{weekly_config_display};padding:0 24px 20px;">
              <div class="settings-config">
                <div class="form-row">
                  <div class="form-field">
                    <label>Wochentag</label>
                    <select id="weeklyDay" {weekly_disabled}>
                      {day_options}
                    </select>
                  </div>
                  <div class="form-field">
                    <label>Uhrzeit</label>
                    <input type="time" id="weeklyTime" value="{weekly_time}" {weekly_disabled}>
                  </div>
                  <div class="form-field" style="flex-direction:row;align-items:flex-end;gap:8px;">
                    <button class="btn btn-primary" onclick="saveWeeklyReport()" {weekly_disabled}>💾 Speichern</button>
                    <button class="btn btn-secondary" onclick="sendReportNow()" {weekly_disabled}>📤 Jetzt senden</button>
                  </div>
                </div>
              </div>
            </div>
            {weekly_upgrade_html}
          </div>
          
        </div>
      </div>
      
      <!-- Sicherheit Card -->
      <div class="content-card" id="security" style="margin-bottom:24px;">
        <div class="content-card-header" style="display:flex;align-items:center;gap:12px;">
          <div style="width:44px;height:44px;background:linear-gradient(135deg,#10b981,#059669);border-radius:12px;display:flex;align-items:center;justify-content:center;">
            <span style="font-size:1.3rem;">🔐</span>
          </div>
          <div>
            <h3 class="content-card-title" style="margin:0;">Sicherheit</h3>
            <p style="margin:2px 0 0;font-size:0.85rem;color:#64748b;">Passwort und Zwei-Faktor-Authentifizierung</p>
          </div>
        </div>
        <div class="content-card-body">
          <form id="passwordForm" onsubmit="changePassword(event)">
            <div class="form-group" style="margin-bottom:16px;">
              <label class="form-label">Aktuelles Passwort</label>
              <input type="password" class="form-input" id="currentPw" required>
            </div>
            <div class="form-group" style="margin-bottom:16px;">
              <label class="form-label">Neues Passwort</label>
              <input type="password" class="form-input" id="newPw" required minlength="8">
            </div>
            <div class="form-group" style="margin-bottom:16px;">
              <label class="form-label">Neues Passwort bestätigen</label>
              <input type="password" class="form-input" id="newPw2" required>
            </div>
            <button type="submit" class="btn btn-primary">🔑 Passwort ändern</button>
          </form>
          
          <div style="border-top:1px solid #e2e8f0;margin:24px 0;"></div>
          
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <strong style="display:block;">🛡️ Zwei-Faktor-Authentifizierung</strong>
              <small style="color:var(--sbs-muted);" id="2faStatusText">Lädt...</small>
            </div>
            <a href="/security" class="btn btn-secondary">2FA verwalten →</a>
          </div>
        </div>
      </div>
      
      <!-- API-Zugang Card -->
      <div class="content-card" id="api" style="margin-bottom:24px;">
        <div class="content-card-header" style="display:flex;align-items:center;gap:12px;">
          <div style="width:44px;height:44px;background:linear-gradient(135deg,#6366f1,#4f46e5);border-radius:12px;display:flex;align-items:center;justify-content:center;">
            <span style="font-size:1.3rem;">🔑</span>
          </div>
          <div>
            <h3 class="content-card-title" style="margin:0;">API-Zugang <span class="badge-enterprise">ENTERPRISE</span></h3>
            <p style="margin:2px 0 0;font-size:0.85rem;color:#64748b;">REST API für Ihre Integrationen</p>
          </div>
        </div>
        <div class="content-card-body">
          <p style="margin-bottom:16px;color:#64748b;">Nutzen Sie unsere REST API für die Integration in Ihre Systeme.</p>
          {api_key_html}
        </div>
      </div>
      
      <!-- Abmelden Card -->
      <div class="content-card" style="border:1px solid #fecaca;">
        <div class="content-card-header" style="display:flex;align-items:center;gap:12px;">
          <div style="width:44px;height:44px;background:linear-gradient(135deg,#ef4444,#dc2626);border-radius:12px;display:flex;align-items:center;justify-content:center;">
            <span style="font-size:1.3rem;">🚪</span>
          </div>
          <div>
            <h3 class="content-card-title" style="margin:0;color:#dc2626;">Abmelden</h3>
            <p style="margin:2px 0 0;font-size:0.85rem;color:#64748b;">Von allen SBS-Anwendungen abmelden</p>
          </div>
        </div>
        <div class="content-card-body">
          <p style="margin-bottom:16px;color:#64748b;">Sie werden von allen SBS-Anwendungen abgemeldet.</p>
          <a href="/logout" class="btn btn-danger">🚪 Jetzt abmelden</a>
        </div>
      </div>
      
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// Toast Notification
function showToast(msg, type) {{
  var t = document.getElementById('toast');
  var icon = type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️';
  t.innerHTML = icon + ' ' + msg;
  t.className = 'toast show';
  t.style.background = type === 'error' ? '#dc2626' : type === 'warning' ? '#f59e0b' : '#1e293b';
  setTimeout(function(){{ t.className = 'toast'; }}, 4000);
}}

// API Key Functions
function copyApiKey() {{
  var code = document.getElementById('apiKeyCode');
  if (code) {{
    navigator.clipboard.writeText(code.textContent);
    showToast('API-Key in Zwischenablage kopiert!', 'success');
  }}
}}

function generateApiKey() {{
  var btn = document.getElementById('generateKeyBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Generiere...';
  
  fetch('/api/settings/generate-key', {{ method: 'POST' }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        var display = document.getElementById('newKeyDisplay');
        display.style.display = 'block';
        display.innerHTML = '<div style="background:#1e293b;border-radius:10px;padding:12px 16px;margin-top:8px;"><code style="color:#22d3ee;word-break:break-all;">' + data.api_key + '</code></div><p style="color:#22c55e;margin-top:8px;font-size:0.85rem;">✅ API-Key generiert! Bitte sicher aufbewahren.</p>';
        btn.style.display = 'none';
        showToast('API-Key erfolgreich generiert!', 'success');
      }} else {{
        showToast(data.error || 'Fehler beim Generieren', 'error');
        btn.disabled = false;
        btn.textContent = 'API-Key generieren';
      }}
    }})
    .catch(function(err) {{
      showToast('Netzwerkfehler', 'error');
      btn.disabled = false;
      btn.textContent = 'API-Key generieren';
    }});
}}

function revokeApiKey() {{
  if (!confirm('API-Key wirklich widerrufen? Alle bestehenden Integrationen werden ungültig.')) return;
  
  fetch('/api/settings/revoke-key', {{ method: 'POST' }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        showToast('API-Key widerrufen', 'success');
        setTimeout(function() {{ location.reload(); }}, 1500);
      }} else {{
        showToast(data.error || 'Fehler', 'error');
      }}
    }});
}}

// E-Mail Notifications
function saveNotifications(type, value) {{
  var fd = new FormData();
  fd.append('notification_' + type, value);
  
  fetch('/api/settings/notifications', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        showToast('E-Mail-Benachrichtigungen ' + (value ? 'aktiviert' : 'deaktiviert'), 'success');
      }} else {{
        showToast(data.error || 'Fehler', 'error');
      }}
    }});
}}

// Slack Functions
function toggleSlackConfig(enabled) {{
  var config = document.getElementById('slackConfig');
  config.style.display = enabled ? 'block' : 'none';
  
  if (!enabled) {{
    // Deaktivieren
    saveSlackSettings(false, '');
  }}
}}

function testSlackWebhook() {{
  var webhook = document.getElementById('slackWebhook').value.trim();
  if (!webhook) {{
    showToast('Bitte Webhook URL eingeben', 'warning');
    return;
  }}
  
  if (!webhook.startsWith('https://hooks.slack.com/')) {{
    showToast('Ungültige Webhook URL - muss mit https://hooks.slack.com/ beginnen', 'error');
    return;
  }}
  
  var btn = document.getElementById('testSlackBtn');
  var originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ Teste...';
  
  var fd = new FormData();
  fd.append('webhook_url', webhook);
  
  fetch('/api/settings/slack/test', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      btn.disabled = false;
      btn.textContent = originalText;
      
      if (data.success) {{
        showToast('Test-Nachricht erfolgreich an Slack gesendet! 🎉', 'success');
      }} else {{
        showToast(data.error || 'Slack-Test fehlgeschlagen', 'error');
      }}
    }})
    .catch(function(err) {{
      btn.disabled = false;
      btn.textContent = originalText;
      showToast('Netzwerkfehler: ' + err.message, 'error');
    }});
}}

function saveSlackWebhook() {{
  var webhook = document.getElementById('slackWebhook').value.trim();
  var enabled = document.getElementById('slackToggle').checked;
  saveSlackSettings(enabled, webhook);
}}

function saveSlackSettings(enabled, webhook) {{
  var fd = new FormData();
  fd.append('enabled', enabled);
  fd.append('webhook_url', webhook);
  
  fetch('/api/settings/slack', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        showToast('Slack-Einstellungen gespeichert!', 'success');
      }} else if (data.upgrade_required) {{
        showToast(data.error, 'warning');
        document.getElementById('slackToggle').checked = false;
        document.getElementById('slackConfig').style.display = 'none';
      }} else {{
        showToast(data.error || 'Fehler beim Speichern', 'error');
      }}
    }});
}}

// Weekly Report Functions
function toggleWeeklyConfig(enabled) {{
  var config = document.getElementById('weeklyConfig');
  config.style.display = enabled ? 'block' : 'none';
  
  if (!enabled) {{
    saveWeeklySettings(false);
  }}
}}

function saveWeeklyReport() {{
  var enabled = document.getElementById('weeklyToggle').checked;
  var day = document.getElementById('weeklyDay').value;
  var time = document.getElementById('weeklyTime').value;
  saveWeeklySettings(enabled, day, time);
}}

function saveWeeklySettings(enabled, day, time) {{
  var fd = new FormData();
  fd.append('enabled', enabled);
  fd.append('day', day || 1);
  fd.append('time', time || '07:00');
  
  fetch('/api/settings/weekly-report', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        var days = ['', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];
        var msg = enabled ? 'Wöchentlicher Report aktiviert (' + days[day] + ' ' + time + ')' : 'Wöchentlicher Report deaktiviert';
        showToast(msg, 'success');
      }} else if (data.upgrade_required) {{
        showToast(data.error, 'warning');
        document.getElementById('weeklyToggle').checked = false;
        document.getElementById('weeklyConfig').style.display = 'none';
      }} else {{
        showToast(data.error || 'Fehler beim Speichern', 'error');
      }}
    }});
}}

function sendReportNow() {{
  if (!confirm('Möchten Sie jetzt einen Report generieren und versenden?')) return;
  
  showToast('Report wird generiert...', 'info');
  
  fetch('/api/reports/send-now', {{ method: 'POST' }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        var msg = 'Report gesendet!';
        if (data.results) {{
          if (data.results.email) msg += ' ✉️ E-Mail';
          if (data.results.slack) msg += ' 💬 Slack';
        }}
        showToast(msg, 'success');
      }} else {{
        showToast(data.error || 'Fehler beim Senden', 'error');
      }}
    }});
}}

// Password Change
function changePassword(e) {{
  e.preventDefault();
  var cur = document.getElementById('currentPw').value;
  var newP = document.getElementById('newPw').value;
  var newP2 = document.getElementById('newPw2').value;
  
  if (newP !== newP2) {{
    showToast('Passwörter stimmen nicht überein', 'error');
    return;
  }}
  
  if (newP.length < 8) {{
    showToast('Passwort muss mindestens 8 Zeichen haben', 'error');
    return;
  }}
  
  var fd = new FormData();
  fd.append('current_password', cur);
  fd.append('new_password', newP);
  
  fetch('/api/change-password', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        showToast('Passwort erfolgreich geändert!', 'success');
        document.getElementById('passwordForm').reset();
      }} else {{
        showToast(data.error || 'Fehler', 'error');
      }}
    }});
}}

// Profile Save
function saveProfile() {{
  var name = document.getElementById('profileName').value;
  var fd = new FormData();
  fd.append('name', name);
  
  fetch('/api/settings/profile', {{ method: 'POST', body: fd }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      if (data.success) {{
        showToast('Profil gespeichert!', 'success');
      }} else {{
        showToast(data.error || 'Fehler', 'error');
      }}
    }})
    .catch(function() {{
      showToast('Profil gespeichert!', 'success');
    }});
}}

// Load 2FA Status
fetch("/api/2fa/status").then(function(r){{return r.json();}}).then(function(data){{
  var el = document.getElementById("2faStatusText");
  if(el) {{
    if(data.enabled) {{
      el.innerHTML = '<span style="color:#22c55e;">✅ Aktiviert</span>';
    }} else {{
      el.innerHTML = '<span style="color:#64748b;">Nicht aktiviert</span>';
    }}
  }}
}}).catch(function(){{
  var el = document.getElementById("2faStatusText");
  if(el) el.textContent = "Status unbekannt";
}});
</script>"""
    
    return page_wrapper("Einstellungen", content, user_name, "settings")


# ============================================================================
# HINWEIS: Diese Funktion benötigt erweiterte user_settings Felder
# ============================================================================
"""
Die get_user_settings() Funktion in enterprise_features.py muss diese Felder zurückgeben:
- user_email
- notification_email
- notification_slack
- slack_webhook_url      <- NEU
- weekly_report_enabled  <- NEU
- weekly_report_day      <- NEU
- weekly_report_time     <- NEU
- api_key

Falls nicht vorhanden, erweitere die Funktion oder nutze Defaults.
"""
