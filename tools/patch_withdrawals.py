from pathlib import Path

ROOT = Path(".")
candidates = list(ROOT.rglob("main.dart"))
if not candidates:
    raise SystemExit("WITHDRAWAL_PATCH_ERROR: main.dart not found")
main = max(candidates, key=lambda p: p.stat().st_size)
text = main.read_text(encoding="utf-8")

start = text.find("class AgentDashboardPage extends StatefulWidget")
end = text.find("class AdminCard", start)
if start < 0 or end < 0:
    raise SystemExit("WITHDRAWAL_PATCH_ERROR: AgentDashboardPage markers not found")
agent = text[start:end]

if "double commissionBalance = 0.0;" not in agent:
    marker = "  int referralCount = 0;"
    if marker not in agent:
        raise SystemExit("WITHDRAWAL_PATCH_ERROR: agent state marker not found")
    agent = agent.replace(marker, marker + "\n  double commissionBalance = 0.0;", 1)

if "Future<void> loadCommissionBalance()" not in agent:
    marker = "  Future<void> refreshAgentDashboard() async {"
    method = r'''  Future<void> loadCommissionBalance() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;
    try {
      final earnedRows = await Supabase.instance.client
          .from('commissions')
          .select('amount')
          .eq('agent_id', user.id)
          .eq('status', 'pending');
      final reservedRows = await Supabase.instance.client
          .from('commission_withdrawals')
          .select('amount')
          .eq('agent_id', user.id)
          .inFilter('status', ['pending', 'approved']);
      double sumAmount(dynamic rows) {
        var total = 0.0;
        for (final row in (rows as List)) {
          final value = row['amount'];
          total += value is num ? value.toDouble() : double.tryParse(value?.toString() ?? '') ?? 0.0;
        }
        return total;
      }
      final available = sumAmount(earnedRows) - sumAmount(reservedRows);
      if (!mounted) return;
      setState(() => commissionBalance = available < 0 ? 0.0 : available);
    } catch (_) {
      if (!mounted) return;
      setState(() => commissionBalance = 0.0);
    }
  }

  Future<void> submitNormalWithdrawal() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;
    final amountController = TextEditingController();
    final phoneController = TextEditingController();
    try {
      final profile = await Supabase.instance.client
          .from('profiles')
          .select('phone')
          .eq('id', user.id)
          .maybeSingle();
      phoneController.text = (profile?['phone'] ?? '').toString();
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          bool submitting = false;
          return StatefulBuilder(
            builder: (context, setDialogState) {
              final available = double.tryParse(balance) ?? 0.0;
              return AlertDialog(
                title: const Text('Withdraw funds'),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text('Available: KES ' + available.toStringAsFixed(2)),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: amountController,
                        enabled: !submitting,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Amount (KES)', prefixText: 'KES '),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: phoneController,
                        enabled: !submitting,
                        keyboardType: TextInputType.phone,
                        decoration: const InputDecoration(labelText: 'M-Pesa phone number', hintText: '07XXXXXXXX'),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: submitting ? null : () => Navigator.pop(dialogContext),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed: submitting ? null : () async {
                      final amount = double.tryParse(amountController.text.trim());
                      final phone = phoneController.text.trim();
                      if (amount == null || amount <= 0 || amount > available || phone.isEmpty) {
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          SnackBar(content: Text(
                            phone.isEmpty
                                ? 'Enter the M-Pesa phone number.'
                                : 'Enter an amount between 0 and KES ' + available.toStringAsFixed(2) + '.',
                          )),
                        );
                        return;
                      }
                      setDialogState(() => submitting = true);
                      try {
                        await Supabase.instance.client.rpc(
                          'request_withdrawal',
                          params: {
                            'p_amount': amount,
                            'p_phone': phone,
                            'p_description': 'Agent account withdrawal request',
                          },
                        );
                        if (!mounted) return;
                        Navigator.pop(dialogContext);
                        await loadAgentData();
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          const SnackBar(
                            content: Text('Withdrawal request submitted and is pending admin processing.'),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      } catch (e) {
                        if (!mounted) return;
                        setDialogState(() => submitting = false);
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          SnackBar(content: Text('Withdrawal request failed: ' + e.toString())),
                        );
                      }
                    },
                    child: submitting
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Request withdrawal'),
                  ),
                ],
              );
            },
          );
        },
      );
    } finally {
      amountController.dispose();
      phoneController.dispose();
    }
  }

  Future<void> submitCommissionWithdrawal() async {
    final user = Supabase.instance.client.auth.currentUser;
    if (user == null) return;
    await loadCommissionBalance();
    final amountController = TextEditingController();
    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) {
          bool submitting = false;
          return StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: const Text('Withdraw commission'),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text('Available commission: KES ' + commissionBalance.toStringAsFixed(2)),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: amountController,
                        enabled: !submitting,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Commission amount (KES)', prefixText: 'KES '),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: submitting ? null : () => Navigator.pop(dialogContext),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed: submitting ? null : () async {
                      final amount = double.tryParse(amountController.text.trim());
                      if (amount == null || amount <= 0 || amount > commissionBalance) {
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          SnackBar(content: Text(
                            'Enter an amount up to KES ' + commissionBalance.toStringAsFixed(2) + '.',
                          )),
                        );
                        return;
                      }
                      setDialogState(() => submitting = true);
                      try {
                        await Supabase.instance.client.rpc(
                          'request_commission_withdrawal',
                          params: {
                            'p_amount': amount,
                            'p_description': 'Agent commission withdrawal request',
                          },
                        );
                        if (!mounted) return;
                        Navigator.pop(dialogContext);
                        await loadCommissionBalance();
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          const SnackBar(
                            content: Text('Commission withdrawal request submitted and is pending admin processing.'),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      } catch (e) {
                        if (!mounted) return;
                        setDialogState(() => submitting = false);
                        ScaffoldMessenger.of(this.context).showSnackBar(
                          SnackBar(content: Text('Commission withdrawal failed: ' + e.toString())),
                        );
                      }
                    },
                    child: submitting
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Request commission'),
                  ),
                ],
              );
            },
          );
        },
      );
    } finally {
      amountController.dispose();
    }
  }

'''
    if marker not in agent:
        raise SystemExit("WITHDRAWAL_PATCH_ERROR: refresh marker not found")
    agent = agent.replace(marker, method + marker, 1)

if "loadCommissionBalance();" not in agent:
    marker = "    loadAgentData();"
    if marker not in agent:
        raise SystemExit("WITHDRAWAL_PATCH_ERROR: init marker not found")
    agent = agent.replace(marker, marker + "\n    loadCommissionBalance();", 1)

if "Commission withdrawal" not in agent:
    marker = """            const Text(
              'Agent actions',"""
    cards = r'''            Card(
              child: ListTile(
                leading: const Icon(Icons.account_balance_wallet_outlined, color: Color(0xFFD9A441)),
                title: const Text('Withdraw funds', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: Text('Available balance: KES ' + (double.tryParse(balance) ?? 0.0).toStringAsFixed(2)),
                trailing: FilledButton(onPressed: submitNormalWithdrawal, child: const Text('Withdraw')),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: ListTile(
                leading: const Icon(Icons.payments_outlined, color: Color(0xFFD9A441)),
                title: const Text('Commission withdrawal', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: Text('Available commission: KES ' + commissionBalance.toStringAsFixed(2)),
                trailing: FilledButton(onPressed: submitCommissionWithdrawal, child: const Text('Withdraw')),
              ),
            ),
            const SizedBox(height: 20),
'''
    if marker not in agent:
        raise SystemExit("WITHDRAWAL_PATCH_ERROR: Agent actions marker not found")
    agent = agent.replace(marker, cards + marker, 1)

text = text[:start] + agent + text[end:]
main.write_text(text, encoding="utf-8")
print("WITHDRAWAL_PATCH_OK")
