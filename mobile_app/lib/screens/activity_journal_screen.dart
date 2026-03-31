import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ActivityJournalScreen extends StatefulWidget {
  const ActivityJournalScreen({super.key});

  @override
  State<ActivityJournalScreen> createState() => _ActivityJournalScreenState();
}

class _ActivityJournalScreenState extends State<ActivityJournalScreen> {
  List<dynamic>? activities;

  @override
  void initState() {
    super.initState();
    loadActivities();
  }

  void loadActivities() async {
    final data = await ApiService().getDashboard(); // Or dedicated activity API
    setState(() => activities = data['activities'] ?? []);
  }

  @override
  Widget build(BuildContext context) {
    // We get the screen width to decide the layout
    double width = MediaQuery.of(context).size.width;
    bool isWide = width > 700; // Tablet or Laptop

    return Scaffold(
      appBar: AppBar(
        title: const Text('FARM JOURNAL', style: TextStyle(color: Color(0xFF1B4332), fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        backgroundColor: Colors.white, elevation: 0, centerTitle: true,
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          return GridView.builder(
            padding: const EdgeInsets.all(20),
            // Multi-column grid for tablets, single list for mobile
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: isWide ? 2 : 1,
              mainAxisExtent: 160,
              crossAxisSpacing: 20,
              mainAxisSpacing: 20,
            ),
            itemCount: activities?.length ?? 4,
            itemBuilder: (context, i) {
              if (activities == null) return _buildSkeleton();
              final a = activities![i];
              return _buildJournalCard(a);
            },
          );
        },
      ),
    );
  }

  Widget _buildJournalCard(dynamic a) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(28), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10)]),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(a['type'].toString().toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.blueGrey, fontSize: 10, letterSpacing: 1.2)),
              const Icon(Icons.history_rounded, size: 14, color: Colors.grey),
            ],
          ),
          const SizedBox(height: 12),
          Text(a['desc'], style: const TextStyle(color: Colors.black87, fontSize: 13, height: 1.5), maxLines: 2, overflow: TextOverflow.ellipsis),
          const Spacer(),
          Text(a['date'] ?? 'Jan 12, 2026', style: const TextStyle(fontSize: 10, color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _buildSkeleton() => Container(decoration: BoxDecoration(color: Colors.white.withOpacity(0.5), borderRadius: BorderRadius.circular(28)));
}
