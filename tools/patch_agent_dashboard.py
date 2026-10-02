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
                  openPage(const NotificationsPage());
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
                  openPage(const NotificationsPage());
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
text = text.replace("""                child: ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: Image.asset(
                    'assets/tombrian_logo.jpg',
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) =>
                        const Icon(
                      Icons.phone_android,
                      size: 32,
                    ),
                  ),
                ),""", """                child: const Icon(
                  Icons.phone_android,
                  size: 32,
                ),""", 1)

text = text.replace("""Image.asset('assets/tombrian_logo.jpg', fit: BoxFit.cover, errorBuilder: (_, __, ___) => const Icon(Icons.phone_android, size: 52, color: Color(0xFFD9A441)))""", """const Icon(Icons.phone_android, size: 52, color: Color(0xFFD9A441))""", 1)



# Preserve and restore the Admin Dashboard commission control.
# The protected 6,810-line recovery source has this control, but the
# main_corrected.zip build source may be an older copy. Inject the same
# Supabase-backed editable percentage control into the build source if it
# is missing, then verify it exists before the build continues.
admin_start = text.find("class AdminDashboardPage extends StatefulWidget")
admin_end = text.find("class AgentDashboardPage", admin_start)
if admin_start < 0 or admin_end < 0:
    raise SystemExit("PATCH_ERROR: Admin Dashboard markers not found")
admin_block = text[admin_start:admin_end]

if "double commissionRate = 0.0;" not in admin_block:
    state_marker = """  List<Map<String, dynamic>> transactions = [];
  List<Map<String, dynamic>> agentApplications = [];
"""
    state_insert = """  List<Map<String, dynamic>> transactions = [];
  List<Map<String, dynamic>> agentApplications = [];

  final commissionRateController = TextEditingController();
  double commissionRate = 0.0;
  bool loadingCommissionRate = true;
  bool savingCommissionRate = false;
"""
    if state_marker not in admin_block:
        raise SystemExit("PATCH_ERROR: Admin state marker not found")
    admin_block = admin_block.replace(state_marker, state_insert, 1)

    init_marker = """  void initState() {
    super.initState();
    loadAdminData();
  }
"""
    init_insert = """  void initState() {
    super.initState();
    loadAdminData();
    loadCommissionRate();
  }

  Future<void> loadCommissionRate() async {
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
      setState(() {
        commissionRate = rate ?? 0.0;
        commissionRateController.text = commissionRate.toStringAsFixed(2);
        loadingCommissionRate = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        loadingCommissionRate = false;
        commissionRate = 0.0;
        commissionRateController.text = '0.00';
      });
    }
  }

  Future<void> saveCommissionRate() async {
    if (savingCommissionRate) return;

    final value = double.tryParse(
      commissionRateController.text.trim().replaceAll('%', ''),
    );

    if (value == null || value < 0 || value > 100) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter a commission rate between 0% and 100%.'),
        ),
      );
      return;
    }

    FocusScope.of(context).unfocus();
    setState(() => savingCommissionRate = true);

    try {
      await Supabase.instance.client.from('commission_settings').upsert(
        {
          'id': 1,
          'commission_rate': value,
          'updated_at': DateTime.now().toIso8601String(),
        },
        onConflict: 'id',
      );

      if (!mounted) return;
      setState(() {
        commissionRate = value;
        commissionRateController.text = value.toStringAsFixed(2);
        savingCommissionRate = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Commission rate updated to ${value.toStringAsFixed(2)}%.',
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => savingCommissionRate = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not update commission rate: $e'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  Widget buildCommissionSettingsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.percent, color: Color(0xFFD9A441)),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Commission Settings',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Set the commission percentage that will be used for eligible agent transactions.',
              style: TextStyle(color: Colors.white60, height: 1.4),
            ),
            const SizedBox(height: 16),
            if (loadingCommissionRate)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Center(child: CircularProgressIndicator()),
              )
            else
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: commissionRateController,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                          RegExp(r'[0-9.]'),
                        ),
                      ],
                      decoration: const InputDecoration(
                        prefixIcon: Icon(Icons.percent),
                        labelText: 'Commission rate',
                        hintText: 'e.g. 5',
                        suffixText: '%',
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    height: 54,
                    child: FilledButton(
                      onPressed:
                          savingCommissionRate ? null : saveCommissionRate,
                      child: savingCommissionRate
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Save'),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
"""
    if init_marker not in admin_block:
        raise SystemExit("PATCH_ERROR: Admin initState marker not found")
    admin_block = admin_block.replace(init_marker, init_insert, 1)

    build_marker = """            const Text(
              'Manage users, balances, transactions and agent applications.',
              style: TextStyle(color: Colors.white60),
            ),
            const SizedBox(height: 20),
"""
    build_insert = """            const Text(
              'Manage users, balances, transactions and agent applications.',
              style: TextStyle(color: Colors.white60),
            ),
            const SizedBox(height: 18),
            buildCommissionSettingsSection(),
            const SizedBox(height: 18),
"""
    if build_marker not in admin_block:
        raise SystemExit("PATCH_ERROR: Admin build intro marker not found")
    admin_block = admin_block.replace(build_marker, build_insert, 1)

    text = text[:admin_start] + admin_block + text[admin_end:]
    print("ADMIN_COMMISSION_INJECTED")
else:
    print("ADMIN_COMMISSION_ALREADY_PRESENT")

admin_start = text.find("class AdminDashboardPage extends StatefulWidget")
admin_end = text.find("class AgentDashboardPage", admin_start)
admin_block = text[admin_start:admin_end]

# Add the Admin transaction history page once so the card above has a real destination.
if "class AdminTransactionsPage extends StatefulWidget" not in text:
    admin_transactions_page = r'''class AdminTransactionsPage extends StatefulWidget {
  const AdminTransactionsPage({super.key});

  @override
  State<AdminTransactionsPage> createState() => _AdminTransactionsPageState();
}

class _AdminTransactionsPageState extends State<AdminTransactionsPage> {
  bool loading = true;
  String? error;
  List<Map<String, dynamic>> transactions = [];

  @override
  void initState() {
    super.initState();
    loadTransactions();
  }

  Future<void> loadTransactions() async {
    final client = Supabase.instance.client;
    final user = client.auth.currentUser;
    if (user == null) {
      if (!mounted) return;
      setState(() {
        loading = false;
        error = 'Please log in as an admin to view transaction history.';
      });
      return;
    }

    if (mounted) setState(() {
      loading = true;
      error = null;
    });

    try {
      final profile = await client
          .from('profiles')
          .select('role')
          .eq('id', user.id)
          .maybeSingle();

      if (profile?['role']?.toString().toLowerCase() != 'admin') {
        throw Exception('Admin authentication required.');
      }

      final data = await client
          .from('transactions')
          .select(
            'id, user_id, amount, transaction_type, description, created_at',
          )
          .order('created_at', ascending: false)
          .limit(200);

      if (!mounted) return;
      setState(() {
        transactions = List<Map<String, dynamic>>.from(data as List);
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        loading = false;
        error = 'Could not load transaction history: $e';
      });
    }
  }

  String formatDate(dynamic value) {
    if (value == null) return 'Unknown date';
    final date = DateTime.tryParse(value.toString());
    if (date == null) return value.toString();
    final d = date.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return d.year.toString() +
        '-' + two(d.month) +
        '-' + two(d.day) +
        ' ' + two(d.hour) +
        ':' + two(d.minute);
  }

  String formatAmount(dynamic value) {
    final amount = value is num
        ? value.toDouble()
        : double.tryParse(value?.toString() ?? '') ?? 0.0;
    return amount.toStringAsFixed(2);
  }

  Widget transactionCard(Map<String, dynamic> tx) {
    final type = (tx['transaction_type'] ?? 'Transaction').toString().trim();
    final description = (tx['description'] ?? '').toString().trim();
    final userId = (tx['user_id'] ?? '').toString();

    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 10,
        ),
        leading: const CircleAvatar(
          backgroundColor: Color(0x22D9A441),
          child: Icon(
            Icons.receipt_long_outlined,
            color: Color(0xFFD9A441),
          ),
        ),
        title: Text(
          type.isEmpty ? 'Transaction' : type,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(
            'User: ' + (userId.isEmpty ? 'Unknown user' : userId) +
                (description.isEmpty ? '' : '
' + description) +
                '
' + formatDate(tx['created_at']),
          ),
        ),
        isThreeLine: true,
        trailing: Text(
          'KES ' + formatAmount(tx['amount']),
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 15,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Transaction History'),
        actions: [
          IconButton(
            tooltip: 'Refresh transactions',
            onPressed: loading ? null : loadTransactions,
            icon: loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: loadTransactions,
        child: loading
            ? ListView(
                children: const [
                  SizedBox(height: 220),
                  Center(child: CircularProgressIndicator()),
                ],
              )
            : error != null
                ? ListView(
                    padding: const EdgeInsets.all(24),
                    children: [
                      const SizedBox(height: 100),
                      const Icon(Icons.error_outline, size: 60),
                      const SizedBox(height: 16),
                      Text(error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      Center(
                        child: FilledButton(
                          onPressed: loadTransactions,
                          child: const Text('Retry'),
                        ),
                      ),
                    ],
                  )
                : transactions.isEmpty
                    ? ListView(
                        padding: const EdgeInsets.all(24),
                        children: const [
                          SizedBox(height: 120),
                          Icon(
                            Icons.receipt_long_outlined,
                            size: 70,
                            color: Color(0xFFD9A441),
                          ),
                          SizedBox(height: 20),
                          Center(
                            child: Text(
                              'No transactions yet.',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      )
                    : ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
                            child: Text(
                              transactions.length.toString() +
                                  ' recent transaction' +
                                  (transactions.length == 1 ? '' : 's'),
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          ...transactions.map(transactionCard),
                          const SizedBox(height: 24),
                        ],
                      ),
      ),
    );
  }
}

'''
    text = text.replace(
        "class AgentDashboardPage extends StatefulWidget",
        admin_transactions_page + "class AgentDashboardPage extends StatefulWidget",
        1,
    )


# Make the Admin Dashboard Transactions card open a real history page.
admin_transactions_card = """                Expanded(
                  child: AdminCard(
                    title: 'Transactions',
                    value: '${transactions.length}',
                    icon: Icons.receipt_long_outlined,
                  ),
                ),
"""
admin_transactions_card_replacement = """                Expanded(
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const AdminTransactionsPage(),
                      ),
                    ),
                    child: AdminCard(
                      title: 'Transactions',
                      value: '${transactions.length}',
                      icon: Icons.receipt_long_outlined,
                    ),
                  ),
                ),
"""
if admin_transactions_card in admin_block:
    admin_block = admin_block.replace(
        admin_transactions_card,
        admin_transactions_card_replacement,
        1,
    )
elif "AdminTransactionsPage" not in admin_block:
    raise SystemExit("PATCH_ERROR: Admin Transactions card marker not found")

# Restore the Admin Dashboard customer-notification action.
if "Future<void> sendNotification()" not in admin_block:
    notification_method = r'''  Future<void> sendNotification() async {
    final titleController = TextEditingController();
    final messageController = TextEditingController();
    String recipient = 'all';
    String? selectedUserId;
    bool sending = false;

    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              final customers = profiles
                  .where((p) => p['role']?.toString().toLowerCase() != 'admin')
                  .toList();

              return AlertDialog(
                title: const Text('Send Notification'),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DropdownButtonFormField<String>(
                        value: recipient,
                        decoration: const InputDecoration(labelText: 'Recipients'),
                        items: const [
                          DropdownMenuItem(value: 'all', child: Text('All customers')),
                          DropdownMenuItem(value: 'specific', child: Text('Specific customer')),
                        ],
                        onChanged: sending ? null : (value) {
                          if (value == null) return;
                          setDialogState(() {
                            recipient = value;
                            if (recipient == 'all') selectedUserId = null;
                          });
                        },
                      ),
                      if (recipient == 'specific') ...[
                        const SizedBox(height: 12),
                        DropdownButtonFormField<String>(
                          value: selectedUserId,
                          decoration: const InputDecoration(labelText: 'Customer'),
                          items: customers.map((customer) {
                            final id = customer['id']?.toString() ?? '';
                            final name = (customer['full_name'] ?? 'Unnamed customer').toString();
                            final phone = (customer['phone'] ?? '').toString();
                            return DropdownMenuItem<String>(
                              value: id,
                              child: Text(phone.isEmpty ? name : '$name — $phone', overflow: TextOverflow.ellipsis),
                            );
                          }).toList(),
                          onChanged: sending ? null : (value) => setDialogState(() => selectedUserId = value),
                        ),
                      ],
                      const SizedBox(height: 12),
                      TextField(
                        controller: titleController,
                        enabled: !sending,
                        maxLength: 100,
                        decoration: const InputDecoration(labelText: 'Title', hintText: 'Example: TomBrian update'),
                      ),
                      const SizedBox(height: 4),
                      TextField(
                        controller: messageController,
                        enabled: !sending,
                        maxLines: 5,
                        maxLength: 1000,
                        decoration: const InputDecoration(labelText: 'Message', hintText: 'Write the notification message...', alignLabelWithHint: true),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(onPressed: sending ? null : () => Navigator.pop(dialogContext), child: const Text('Cancel')),
                  FilledButton.icon(
                    onPressed: sending ? null : () async {
                      final title = titleController.text.trim();
                      final message = messageController.text.trim();
                      if (title.isEmpty || message.isEmpty) {
                        ScaffoldMessenger.of(this.context).showSnackBar(const SnackBar(content: Text('Enter both a notification title and message.')));
                        return;
                      }
                      if (recipient == 'specific' && (selectedUserId == null || selectedUserId!.isEmpty)) {
                        ScaffoldMessenger.of(this.context).showSnackBar(const SnackBar(content: Text('Select a customer first.')));
                        return;
                      }
                      setDialogState(() => sending = true);
                      try {
                        final userIds = recipient == 'all'
                            ? profiles.where((p) => p['role']?.toString().toLowerCase() != 'admin').map((p) => p['id']?.toString() ?? '').where((id) => id.isNotEmpty).toList()
                            : <String>[selectedUserId!];
                        if (userIds.isEmpty) throw Exception('No customer accounts were found.');
                        final now = DateTime.now().toIso8601String();
                        final rows = userIds.map((userId) => <String, dynamic>{
                          'user_id': userId,
                          'title': title,
                          'message': message,
                          'is_read': false,
                          'created_at': now,
                        }).toList();
                        await Supabase.instance.client.from('notifications').insert(rows);
                        if (!mounted) return;
                        Navigator.pop(dialogContext);
                        ScaffoldMessenger.of(this.context).showSnackBar(SnackBar(content: Text('Notification sent successfully.')));
                      } catch (e) {
                        if (!mounted) return;
                        setDialogState(() => sending = false);
                        ScaffoldMessenger.of(this.context).showSnackBar(SnackBar(content: Text('Could not send notification: $e')));
                      }
                    },
                    icon: sending ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.send),
                    label: Text(sending ? 'Sending...' : 'Send'),
                  ),
                ],
              );
            },
          );
        },
      );
    } finally {
      titleController.dispose();
      messageController.dispose();
    }
  }

'''
    admin_marker = "  Future<void> logout() async {"
    if admin_marker not in admin_block:
        raise SystemExit("PATCH_ERROR: Admin logout marker not found")
    admin_block = admin_block.replace(admin_marker, notification_method + admin_marker, 1)

notification_card_marker = """            buildAgentApplicationsSection(),
"""
notification_card_insert = """            Card(
              child: ListTile(
                leading: const Icon(
                  Icons.notifications_active_outlined,
                  color: Color(0xFFD9A441),
                ),
                title: const Text(
                  'Customer Notifications',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: const Text(
                  'Send an in-app message to all customers or one customer.',
                ),
                trailing: FilledButton.icon(
                  onPressed: sendNotification,
                  icon: const Icon(Icons.send),
                  label: const Text('Send'),
                ),
              ),
            ),
            const SizedBox(height: 20),
            buildAgentApplicationsSection(),
"""
if notification_card_marker not in admin_block:
    raise SystemExit("PATCH_ERROR: Admin applications section marker not found")
admin_block = admin_block.replace(notification_card_marker, notification_card_insert, 1)

text = text[:admin_start] + admin_block + text[admin_end:]
print("ADMIN_NOTIFICATIONS_RESTORED")

admin_start = text.find("class AdminDashboardPage extends StatefulWidget")
admin_end = text.find("class AgentDashboardPage", admin_start)
admin_block = text[admin_start:admin_end]
required_admin_commission_markers = [
    "buildCommissionSettingsSection()",
    "Commission Settings",
    "Commission rate",
    "saveCommissionRate",
    "sendNotification()",
    "Customer Notifications",
]
missing_admin_markers = [
    marker for marker in required_admin_commission_markers
    if marker not in admin_block
]
if missing_admin_markers:
    raise SystemExit(
        "PATCH_ERROR: Admin commission control missing: "
        + ", ".join(missing_admin_markers)
    )
print("ADMIN_COMMISSION_OK")

# Final refinement: the Agent Dashboard should have only the bell icon.
import re

agent_start = text.find("class AgentDashboardPage extends StatefulWidget")
agent_end = text.find("class AdminCard", agent_start)
if agent_start < 0 or agent_end < 0:
    raise SystemExit("PATCH_ERROR: Agent Dashboard markers not found during refinement")

agent = text[agent_start:agent_end]
agent = re.sub(r"\n  Future<void> loadUnreadNotificationCount\(\) async \{.*?\n  \}\n", "\n", agent, flags=re.S)
agent = agent.replace("\n  int unreadNotificationCount = 0;", "")
agent = agent.replace("\n      await loadUnreadNotificationCount();", "")

agent = re.sub(
    r"\n          Stack\(\s*alignment: Alignment\.center,\s*children: \[.*?\n          \),\n          IconButton\(\s*tooltip: 'Refresh dashboard'",
    "\n          IconButton(\n            tooltip: 'Notifications',\n            onPressed: () => openPage(const NotificationsPage()),\n            icon: const Icon(Icons.notifications_none),\n          ),\n          IconButton(\n            tooltip: 'Refresh dashboard'",
    agent,
    flags=re.S,
)

agent = re.sub(
    r"\n            const SizedBox\(height: 12\),\n            Card\(\s*child: ListTile\(\s*leading: const Icon\(\s*Icons\.notifications_none,.*?\n            \),\n            const SizedBox\(height: 24\),",
    "\n            const SizedBox(height: 24),",
    agent,
    flags=re.S,
)

text = text[:agent_start] + agent + text[agent_end:]

ns = text.find("class NotificationsPage extends StatelessWidget")
ne = text.find("class TransactionsPage extends StatelessWidget", ns)
if ns < 0 or ne < 0:
    raise SystemExit("PATCH_ERROR: NotificationsPage markers not found during refinement")

notifications_page = r'''class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  bool loading = true;
  bool markingAllRead = false;
  String? error;
  List<Map<String, dynamic>> notifications = [];
  List<Map<String, dynamic>> transactions = [];

  @override
  void initState() {
    super.initState();
    loadActivity();
  }

  Future<void> loadActivity() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          loading = false;
          error = 'Please log in to view account activity.';
        });
      }
      return;
    }

    if (mounted) {
      setState(() {
        loading = true;
        error = null;
      });
    }

    try {
      final client = Supabase.instance.client;

      final notificationData = await client
          .from('notifications')
          .select('id, title, message, is_read, created_at')
          .eq('user_id', user.id)
          .order('created_at', ascending: false)
          .limit(50);

      final transactionData = await client
          .from('transactions')
          .select('id, amount, transaction_type, created_at')
          .eq('user_id', user.id)
          .order('created_at', ascending: false)
          .limit(50);

      if (!mounted) return;
      setState(() {
        notifications = List<Map<String, dynamic>>.from(notificationData as List);
        transactions = List<Map<String, dynamic>>.from(transactionData as List);
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        loading = false;
        error = 'Could not load account activity: $e';
      });
    }
  }

  String formatDate(dynamic value) {
    if (value == null) return '';
    final date = DateTime.tryParse(value.toString());
    if (date == null) return value.toString();
    final d = date.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return '\${d.year}-\${two(d.month)}-\${two(d.day)} \${two(d.hour)}:\${two(d.minute)}';
  }

  Future<void> markAsRead(Map<String, dynamic> notification) async {
    final id = notification['id'];
    if (id == null || notification['is_read'] == true) return;

    try {
      await Supabase.instance.client
          .from('notifications')
          .update({'is_read': true})
          .eq('id', id);

      if (!mounted) return;
      setState(() => notification['is_read'] = true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not mark notification as read: $e')),
      );
    }
  }

  Future<void> markAllAsRead() async {
    if (markingAllRead) return;
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;

    setState(() => markingAllRead = true);
    try {
      await Supabase.instance.client
          .from('notifications')
          .update({'is_read': true})
          .eq('user_id', user.id)
          .eq('is_read', false);

      if (!mounted) return;
      setState(() {
        for (final item in notifications) {
          item['is_read'] = true;
        }
        markingAllRead = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => markingAllRead = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not mark notifications as read: $e')),
      );
    }
  }

  Widget transactionCard(Map<String, dynamic> tx) {
    final type = (tx['transaction_type'] ?? 'Transaction').toString();
    final amount = (tx['amount'] ?? 0).toString();

    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: const CircleAvatar(
          backgroundColor: Color(0x22D9A441),
          child: Icon(Icons.receipt_long_outlined, color: Color(0xFFD9A441)),
        ),
        title: Text(type, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(formatDate(tx['created_at'])),
        ),
        trailing: Text(
          'KES $amount',
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
        ),
      ),
    );
  }

  Widget notificationCard(Map<String, dynamic> notification) {
    final isUnread = notification['is_read'] != true;
    final title = (notification['title'] ?? 'TomBrian notification').toString();
    final message = (notification['message'] ?? '').toString();

    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: CircleAvatar(
          backgroundColor: const Color(0x22D9A441),
          child: Icon(
            isUnread ? Icons.notifications_active_outlined : Icons.notifications_none,
            color: const Color(0xFFD9A441),
          ),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: TextStyle(fontWeight: isUnread ? FontWeight.w800 : FontWeight.w600),
              ),
            ),
            if (isUnread)
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(message),
              const SizedBox(height: 8),
              Text(
                formatDate(notification['created_at']),
                style: const TextStyle(color: Colors.white54, fontSize: 12),
              ),
            ],
          ),
        ),
        onTap: () => markAsRead(notification),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final unread = notifications.where((n) => n['is_read'] != true).length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Account Activity'),
        actions: [
          if (unread > 0)
            IconButton(
              tooltip: 'Mark all messages as read',
              onPressed: markingAllRead ? null : markAllAsRead,
              icon: markingAllRead
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.done_all),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: loadActivity,
        child: loading
            ? ListView(
                children: const [
                  SizedBox(height: 220),
                  Center(child: CircularProgressIndicator()),
                ],
              )
            : error != null
                ? ListView(
                    padding: const EdgeInsets.all(24),
                    children: [
                      const SizedBox(height: 100),
                      const Icon(Icons.error_outline, size: 60),
                      const SizedBox(height: 16),
                      Text(error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      Center(
                        child: FilledButton(
                          onPressed: loadActivity,
                          child: const Text('Retry'),
                        ),
                      ),
                    ],
                  )
                : (transactions.isEmpty && notifications.isEmpty)
                    ? ListView(
                        padding: const EdgeInsets.all(24),
                        children: const [
                          SizedBox(height: 130),
                          Icon(Icons.receipt_long_outlined, size: 70, color: Color(0xFFD9A441)),
                          SizedBox(height: 20),
                          Center(
                            child: Text('No account activity yet', style: TextStyle(fontSize: 20)),
                          ),
                          SizedBox(height: 8),
                          Center(
                            child: Text(
                              'Your real transactions and TomBrian messages will appear here.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Colors.white54),
                            ),
                          ),
                        ],
                      )
                    : ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          if (transactions.isNotEmpty) ...[
                            const Padding(
                              padding: EdgeInsets.fromLTRB(4, 4, 4, 10),
                              child: Text(
                                'Recent transactions',
                                style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
                              ),
                            ),
                            ...transactions.map(transactionCard),
                          ],
                          if (notifications.isNotEmpty) ...[
                            const SizedBox(height: 20),
                            const Padding(
                              padding: EdgeInsets.fromLTRB(4, 4, 4, 10),
                              child: Text(
                                'TomBrian messages',
                                style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
                              ),
                            ),
                            ...notifications.map(notificationCard),
                          ],
                          const SizedBox(height: 24),
                        ],
                      ),
      ),
    );
  }
}

'''
text = text[:ns] + notifications_page + text[ne:]

# Replace the placeholder Transaction History page with a real Supabase-backed
# history view. This changes only the build copy, not the protected source.
transactions_start = text.find("class TransactionsPage extends StatelessWidget")
transactions_end = text.find("class AccountPage extends StatelessWidget", transactions_start)
if transactions_start < 0 or transactions_end < 0:
    raise SystemExit("PATCH_ERROR: TransactionsPage markers not found")

transactions_page = r'''class TransactionsPage extends StatefulWidget {
  const TransactionsPage({super.key});

  @override
  State<TransactionsPage> createState() => _TransactionsPageState();
}

class _TransactionsPageState extends State<TransactionsPage> {
  bool loading = true;
  String? error;
  List<Map<String, dynamic>> transactions = [];

  @override
  void initState() {
    super.initState();
    loadTransactions();
  }

  Future<void> loadTransactions() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) {
      if (!mounted) return;
      setState(() {
        loading = false;
        error = 'Please log in to view your transaction history.';
      });
      return;
    }

    if (mounted) {
      setState(() {
        loading = true;
        error = null;
      });
    }

    try {
      final data = await Supabase.instance.client
          .from('transactions')
          .select('id, amount, transaction_type, description, created_at')
          .eq('user_id', user.id)
          .order('created_at', ascending: false)
          .limit(100);

      if (!mounted) return;
      setState(() {
        transactions = List<Map<String, dynamic>>.from(data as List);
        loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        loading = false;
        error = 'Could not load transaction history: ' + e.toString();
      });
    }
  }

  String formatDate(dynamic value) {
    if (value == null) return '';
    final date = DateTime.tryParse(value.toString());
    if (date == null) return value.toString();
    final local = date.toLocal();
    String two(int n) => n.toString().padLeft(2, '0');
    return local.year.toString() +
        '-' + two(local.month) +
        '-' + two(local.day) +
        ' ' + two(local.hour) +
        ':' + two(local.minute);
  }

  String formatAmount(dynamic value) {
    final amount = value is num
        ? value.toDouble()
        : double.tryParse(value?.toString() ?? '') ?? 0.0;
    return amount.toStringAsFixed(2);
  }

  Widget transactionCard(Map<String, dynamic> transaction) {
    final type = (transaction['transaction_type'] ?? 'Transaction')
        .toString()
        .trim();
    final description = (transaction['description'] ?? '').toString().trim();
    final subtitle = description.isEmpty
        ? formatDate(transaction['created_at'])
        : description + ' - ' + formatDate(transaction['created_at']);

    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 8,
        ),
        leading: const CircleAvatar(
          backgroundColor: Color(0x22D9A441),
          child: Icon(
            Icons.receipt_long_outlined,
            color: Color(0xFFD9A441),
          ),
        ),
        title: Text(
          type.isEmpty ? 'Transaction' : type,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(subtitle),
        ),
        isThreeLine: description.isNotEmpty,
        trailing: Text(
          'KES ' + formatAmount(transaction['amount']),
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 15,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transaction History'),
        actions: [
          IconButton(
            tooltip: 'Refresh transactions',
            onPressed: loading ? null : loadTransactions,
            icon: loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: loadTransactions,
        child: loading
            ? ListView(
                children: const [
                  SizedBox(height: 220),
                  Center(child: CircularProgressIndicator()),
                ],
              )
            : error != null
                ? ListView(
                    padding: const EdgeInsets.all(24),
                    children: [
                      const SizedBox(height: 100),
                      const Icon(Icons.error_outline, size: 60),
                      const SizedBox(height: 16),
                      Text(error!, textAlign: TextAlign.center),
                      const SizedBox(height: 16),
                      Center(
                        child: FilledButton(
                          onPressed: loadTransactions,
                          child: const Text('Retry'),
                        ),
                      ),
                    ],
                  )
                : transactions.isEmpty
                    ? ListView(
                        padding: const EdgeInsets.all(24),
                        children: const [
                          SizedBox(height: 120),
                          Icon(
                            Icons.receipt_long_outlined,
                            size: 70,
                            color: Color(0xFFD9A441),
                          ),
                          SizedBox(height: 20),
                          Center(
                            child: Text(
                              'No transactions yet.',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          SizedBox(height: 8),
                          Center(
                            child: Text(
                              'Your completed TomBrian transactions will appear here.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Colors.white54),
                            ),
                          ),
                        ],
                      )
                    : ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(4, 4, 4, 12),
                            child: Text(
                              transactions.length.toString() +
                                  ' recent transaction' +
                                  (transactions.length == 1 ? '' : 's'),
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          ...transactions.map(transactionCard),
                          const SizedBox(height: 24),
                        ],
                      ),
      ),
    );
  }
}

'''
text = text[:transactions_start] + transactions_page + text[transactions_end:]
print("PATCH_OK: TRANSACTIONS_PAGE_REAL")


main.write_text(text, encoding="utf-8")
print("PATCH_OK:", main)
