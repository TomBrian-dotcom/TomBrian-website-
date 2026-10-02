from pathlib import Path

ROOT = Path(".")
candidates = list(ROOT.rglob("main.dart"))
if not candidates:
    raise SystemExit("PATCH_ERROR: no main.dart found after extracting main_corrected.zip")
main = max(candidates, key=lambda p: p.stat().st_size)
text = main.read_text(encoding="utf-8")

start = text.find("class AgentDashboardPage extends StatefulWidget")
end = text.find("class AdminCard", start)
if start < 0 or end < 0:
    raise SystemExit("PATCH_ERROR: AgentDashboardPage markers not found")
block = text[start:end]

if "double commissionRate = 0.0;" in block:
    print("Agent Dashboard patch already present")
    raise SystemExit(0)

old = """  static const storage = FlutterSecureStorage();
  static const loginFlagKey = 'tombrian_logged_in';

  bool loading = true;
  String userName = 'Agent';
  String balance = '0.00';
  int referralCount = 0;"""
new = """  static const storage = FlutterSecureStorage();
  static const loginFlagKey = 'tombrian_logged_in';

  bool loading = true;
  bool refreshing = false;
  String userName = 'Agent';
  String balance = '0.00';
  int referralCount = 0;
  double commissionRate = 0.0;
  int unreadNotificationCount = 0;"""
if old not in block:
    raise SystemExit("PATCH_ERROR: Agent state marker not found")
block = block.replace(old, new, 1)

old = """  @override
  void initState() {
    super.initState();
    loadAgentData();
  }

  Future<void> loadAgentData() async {"""
new = """  @override
  void initState() {
    super.initState();
    loadAgentData();
  }

  Future<void> loadAgentCommissionRate() async {
    try {
      final data = await Supabase.instance.client
          .from('commission_settings')
          .select('commission_rate')
          .eq('id', 1)
          .maybeSingle();

      final value = data?['commission_rate'];
      final rate = value is num
          ? value.toDouble()
          : double.tryParse(value?.toString() ?? '');

      if (!mounted) return;
      setState(() => commissionRate = rate ?? 0.0);
    } catch (_) {}
  }

  Future<void> loadUnreadNotificationCount() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;

    try {
      final data = await Supabase.instance.client
          .from('notifications')
          .select('id')
          .eq('user_id', user.id)
          .eq('is_read', false);

      if (!mounted) return;
      setState(() => unreadNotificationCount = (data as List).length);
    } catch (_) {}
  }

  Future<void> refreshAgentDashboard() async {
    if (refreshing) return;
    if (mounted) setState(() => refreshing = true);

    try {
      await loadAgentData();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Agent dashboard refreshed.')),
        );
      }
    } finally {
      if (mounted) setState(() => refreshing = false);
    }
  }

  Future<void> loadAgentData() async {"""
if old not in block:
    raise SystemExit("PATCH_ERROR: initState marker not found")
block = block.replace(old, new, 1)

old = """        final referrals = await client
            .from('referrals')
            .select('id')
            .eq('referrer_id', user.id);
        referralCount = (referrals as List).length;
      } catch (_) {}

      if (!mounted) return;"""
new = """        final referrals = await client
            .from('referrals')
            .select('id')
            .eq('referrer_id', user.id);
        referralCount = (referrals as List).length;
      } catch (_) {}

      await loadAgentCommissionRate();
      await loadUnreadNotificationCount();

      if (!mounted) return;"""
if old not in block:
    raise SystemExit("PATCH_ERROR: referral marker not found")
block = block.replace(old, new, 1)

old = """      appBar: AppBar(
        title: const Text('Agent Dashboard'),
        actions: [
          IconButton(
            onPressed: loadAgentData,
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),"""
new = """      appBar: AppBar(
        title: const Text('Agent Dashboard'),
        actions: [
          Stack(
            alignment: Alignment.center,
            children: [
              IconButton(
                tooltip: 'Notifications',
                onPressed: () async {
                  await openPage(const NotificationsPage());
                  await loadUnreadNotificationCount();
                },
                icon: const Icon(Icons.notifications_none),
              ),
              if (unreadNotificationCount > 0)
                Positioned(
                  right: 7,
                  top: 7,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 5,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.red,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      unreadNotificationCount > 99
                          ? '99+'
                          : '__DOLLAR__{unreadNotificationCount}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            tooltip: 'Refresh dashboard',
            onPressed: refreshing ? null : refreshAgentDashboard,
            icon: refreshing
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),"""
if old not in block:
    raise SystemExit("PATCH_ERROR: AppBar marker not found")
block = block.replace(old, new, 1)

marker = """            const SizedBox(height: 24),
            const Text(
              'Agent actions',"""
insert = """            const SizedBox(height: 20),
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.percent,
                  color: Color(0xFFD9A441),
                ),
                title: const Text('Commission rate'),
                subtitle: const Text(
                  'Current TomBrian agent commission percentage.',
                ),
                trailing: Text(
                  '__DOLLAR__{commissionRate.toStringAsFixed(2)}%',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.notifications_none,
                  color: Color(0xFFD9A441),
                ),
                title: const Text('Notifications'),
                subtitle: Text(
                  unreadNotificationCount == 0
                      ? 'No unread notifications.'
                      : '__DOLLAR__{unreadNotificationCount} unread notification__DOLLAR__{unreadNotificationCount == 1 ? '' : 's'}.',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () async {
                  await openPage(const NotificationsPage());
                  await loadUnreadNotificationCount();
                },
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Agent actions',"""
if marker not in block:
    raise SystemExit("PATCH_ERROR: Agent actions marker not found")
block = block.replace(marker, insert, 1)

block = block.replace("__DOLLAR__", chr(36))
text = text[:start] + block + text[end:]
main.write_text(text, encoding="utf-8")
print("PATCH_OK:", main)
