import 'package:flutter/material.dart';
import '../services/api_service.dart';

class MarketPricesScreen extends StatefulWidget {
  const MarketPricesScreen({super.key});

  @override
  State<MarketPricesScreen> createState() => _MarketPricesScreenState();
}

class _MarketPricesScreenState extends State<MarketPricesScreen> {
  List<dynamic>? prices;

  @override
  void initState() {
    super.initState();
    loadPrices();
  }

  void loadPrices() async {
    final p = await ApiService().getMarketPrices();
    setState(() => prices = p);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MARKET PRICES', style: TextStyle(color: Color(0xFF1B4332), fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        backgroundColor: Colors.white, elevation: 0, centerTitle: true,
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(20),
        itemCount: prices?.length ?? 5,
        itemBuilder: (context, i) {
          if (prices == null) return _buildSkeletonRow();
          final p = prices![i];
          return Container(
            padding: const EdgeInsets.all(15),
            margin: const EdgeInsets.only(bottom: 15),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(25), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10)]),
            child: Row(
              children: [
                ClipRRect(borderRadius: BorderRadius.circular(15), child: Image.network(p['img_url'] ?? 'https://via.placeholder.com/60', width: 60, height: 60, fit: BoxFit.fill)),
                const SizedBox(width: 15),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(p['name'].toString().toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF1B4332))),
                      const SizedBox(height: 3),
                      Text('${p['market']}, ${p['state']}', style: const TextStyle(fontSize: 10, color: Colors.grey, fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('₹${p['price_modal']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Color(0xFF1B4332))),
                    const Text('per quintal', style: TextStyle(fontSize: 8, color: Colors.grey)),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildSkeletonRow() {
    return Container(
      height: 90, margin: const EdgeInsets.only(bottom: 15),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.5), borderRadius: BorderRadius.circular(25)),
    );
  }
}
