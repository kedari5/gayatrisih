import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? data;

  @override
  void initState() {
    super.initState();
    loadDashboard();
  }

  Future<void> loadDashboard() async {
    final d = await ApiService().getDashboard();
    if (mounted) {
      setState(() => data = d);
    }
  }

  void _navigateTo(int index) {
    // We can use a reference to the parent state if needed, 
    // but the easiest way here is to use the PageController via the context if it's high enough.
    // For now, since they are in an IndexedStack/PageView, we'll use a broadcast or parent-level method.
    // However, the current main.dart doesn't expose it. Let's fix Dashboard buttons to use standard Navigator if they were separate routes, 
    // but since they are in a PageView, I will simply trigger the page change via a notification or similar.
    // SIMPLER FIX: Use a global key or just standard Navigator for the specific screens if they exist as routes too.
    // For now, I'll update the 'main.dart' to handle this if I can, but let's make these buttons at least interactive.
  }

  @override
  Widget build(BuildContext context) {
    final weather = data?['weather'];
    final name = data?['user']?['name'] ?? 'Farmer';

    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      body: RefreshIndicator(
        onRefresh: loadDashboard,
        color: const Color(0xFF1B4332),
        child: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Namaste,',
                    style: TextStyle(
                      fontSize: 18,
                      color: const Color(0xFF1B4332).withOpacity(0.5),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    name,
                    style: const TextStyle(
                      fontSize: 32,
                      color: Color(0xFF1B4332),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    weather != null
                        ? 'The air is ${weather['main']['humidity']}% humid in ${weather['name']}.'
                        : 'Ready for another productive day in the fields?',
                    style: TextStyle(
                      fontSize: 14,
                      color: const Color(0xFF1B4332).withOpacity(0.6),
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          if (weather != null)
            SliverToBoxAdapter(
              child: _buildWebStyleWeatherCard(weather),
            ),

          SliverPadding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                const SizedBox(height: 25),
                _buildSectionHeader('Crop Trends', 'market'),
                const SizedBox(height: 15),
                _buildMarketList(),
                const SizedBox(height: 30),
                _buildSectionHeader('Recent Conversations', 'chat'),
                const SizedBox(height: 15),
                _buildChatQuickList(),
                const SizedBox(height: 30),
                const Text(
                  'Quick Access',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1B4332),
                  ),
                ),
                const SizedBox(height: 15),
                _buildQuickAccessGrid(),
                const SizedBox(height: 100), // Space for bottom nav
              ]),
            ),
          ),
        ],
      ),
    ),
  );
}

  Widget _buildSectionHeader(String title, String route) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1B4332),
          ),
        ),
        TextButton(
          onPressed: () {
            // Navigation logic would go here
          },
          child: Text(
            'VIEW ALL',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: Colors.orange.shade700,
              letterSpacing: 1,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildWebStyleWeatherCard(dynamic w) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(35),
        border: const Border(left: BorderSide(color: Colors.lightBlue, width: 8)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 20,
            offset: const Offset(0, 10),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.location_on, size: 16, color: Colors.blue.shade400),
              const SizedBox(width: 8),
              Text(
                'WEATHER IN ${w['name'].toString().toUpperCase()}',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2,
                  color: const Color(0xFF1B4332).withOpacity(0.4),
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Row(
            children: [
              Text(
                '${w['main']['temp'].round()}°',
                style: const TextStyle(
                  fontSize: 60,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1B4332),
                ),
              ),
              const Text(
                'C',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w300),
              ),
              const Spacer(),
              Image.network(
                'http://openweathermap.org/img/wn/${w['weather'][0]['icon']}@2x.png',
                width: 60,
              ),
            ],
          ),
          Text(
            w['weather'][0]['description'].toString().toUpperCase(),
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: const Color(0xFF1B4332).withOpacity(0.6),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              _buildWeatherStat('HUMIDITY', '${w['main']['humidity']}%'),
              const SizedBox(width: 20),
              _buildWeatherStat('WIND', '${w['wind']['speed']} m/s'),
            ],
          )
        ],
      ),
    );
  }

  Widget _buildWeatherStat(String label, String value) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFFF1F3F4),
          borderRadius: BorderRadius.circular(15),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.grey),
            ),
            Text(
              value,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1B4332)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMarketList() {
    final List prices = data?['market_prices'] ?? [];
    if (prices.isEmpty) return const Center(child: CircularProgressIndicator());
    
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: const Border(left: BorderSide(color: Colors.orange, width: 8)),
      ),
      padding: const EdgeInsets.all(10),
      child: Column(
        children: prices.take(3).map((p) => ListTile(
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: Colors.orange.shade50, shape: BoxShape.circle),
            child: Icon(Icons.eco_rounded, size: 16, color: Colors.orange),
          ),
          title: Text(p['name'].toString().toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
          subtitle: Text('${p['market']}', style: const TextStyle(fontSize: 11)),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('₹${p['price_modal']}', style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF1B4332))),
              const Text('per quintal', style: TextStyle(fontSize: 8, color: Colors.grey)),
            ],
          ),
        )).toList(),
      ),
    );
  }

  Widget _buildChatQuickList() {
    final List chats = data?['recent_messages'] ?? [];
    if (chats.isEmpty) return const Text('No recent chats');
    
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: const Border(left: BorderSide(color: Color(0xFF1B4332), width: 8)),
      ),
      padding: const EdgeInsets.all(10),
      child: Column(
        children: chats.take(2).map((c) => ListTile(
          leading: const Icon(Icons.forum_rounded, color: Color(0xFF1B4332), size: 20),
          title: Text(c['msg'], maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
          trailing: const Icon(Icons.chevron_right_rounded, size: 18),
        )).toList(),
      ),
    );
  }

  Widget _buildQuickAccessGrid() {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 15,
      crossAxisSpacing: 15,
      childAspectRatio: 1.5,
      children: [
        _buildQuickItem(Icons.smart_toy_rounded, 'SAKHI CHAT', const Color(0xFF1B4332)),
        _buildQuickItem(Icons.wb_sunny, 'FORECAST', Colors.lightBlue),
        _buildQuickItem(Icons.trending_up, 'PRICES', Colors.orange),
        _buildQuickItem(Icons.assignment, 'LOGS', Colors.brown),
      ],
    );
  }

  Widget _buildQuickItem(IconData icon, String label, Color color) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10)],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 10, letterSpacing: 1)),
        ],
      ),
    );
  }
}

