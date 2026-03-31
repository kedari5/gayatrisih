import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Use your real IP or http://10.0.2.2/ for Android emulator
  final String baseUrl = 'http://172.250.1.183:5000';

  // Store session cookie to maintain login state
  String? _sessionCookie;

  Future<bool> signup({
    required String name,
    required String phone,
    required String password,
    required String language,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/signup'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'phone_number': phone,
          'password': password,
          'language_preference': language,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 302) {
        _sessionCookie = response.headers['set-cookie'];
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Future<bool> login(String phone, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'phone_number': phone, 'password': password}),
      );

      if (response.statusCode == 200 || response.statusCode == 302) {
        _sessionCookie = response.headers['set-cookie'];
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  Map<String, String> _getHeaders() {
    final headers = {'Content-Type': 'application/json'};
    if (_sessionCookie != null) {
      headers['cookie'] = _sessionCookie!;
    }
    return headers;
  }

  Future<Map<String, dynamic>> sendChatMessage(String message) async {
    final response = await http.post(
      Uri.parse('$baseUrl/send_message'),
      headers: _getHeaders(),
      body: jsonEncode({'message': message}),
    );
    return jsonDecode(response.body);
  }

  Future<List<dynamic>> getMarketPrices() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/market_prices'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);
      return decoded['data'] ?? [];
    }
    return [];
  }

  Future<Map<String, dynamic>> getDashboard() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/dashboard'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      try {
        return jsonDecode(response.body);
      } catch (e) {
        return {};
      }
    }
    return {};
  }
}
