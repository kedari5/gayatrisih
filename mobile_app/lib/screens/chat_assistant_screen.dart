import 'package:flutter/material.dart';
import '../services/api_service.dart';

class ChatAssistantScreen extends StatefulWidget {
  const ChatAssistantScreen({super.key});

  @override
  State<ChatAssistantScreen> createState() => _ChatAssistantScreenState();
}

class _ChatAssistantScreenState extends State<ChatAssistantScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<Map<String, String>> _messages = [];
  bool _isLoading = false;

  void _sendMessage() async {
    if (_controller.text.isEmpty) return;
    String userText = _controller.text;
    setState(() {
      _messages.add({'sender': 'user', 'text': userText});
      _isLoading = true;
    });
    _controller.clear();

    try {
      final data = await ApiService().sendChatMessage(userText);
      if (!mounted) return;
      setState(() {
        _messages.add({'sender': 'bot', 'text': data['response']});
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Server Error. Check connection.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Column(children: [
          Text('SAKHI AI', style: TextStyle(color: Color(0xFF1B4332), fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          Text('Always active', style: TextStyle(color: Colors.green, fontSize: 10, fontWeight: FontWeight.bold)),
        ]),
        backgroundColor: Colors.white.withOpacity(0.9), elevation: 0, centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(20),
              itemCount: _messages.length,
              itemBuilder: (context, i) {
                bool isUser = _messages[i]['sender'] == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: isUser ? const Color(0xFF1B4332) : const Color(0xFFF1F3F4),
                      borderRadius: BorderRadius.circular(24).copyWith(
                        bottomRight: isUser ? const Radius.circular(0) : const Radius.circular(24),
                        bottomLeft: isUser ? const Radius.circular(24) : const Radius.circular(0),
                      ),
                    ),
                    child: Text(_messages[i]['text']!, style: TextStyle(color: isUser ? Colors.white : Colors.black87, height: 1.4)),
                  ),
                );
              },
            ),
          ),
          if (_isLoading) const Padding(padding: EdgeInsets.all(8.0), child: CircularProgressIndicator(color: Color(0xFF1B4332), strokeWidth: 2)),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: Color(0xFFF1F3F4)))),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              style: const TextStyle(fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Ask anything about crops or weather...',
                filled: true, fillColor: const Color(0xFFF8F9FA),
                prefixIcon: const Icon(Icons.mic_none_outlined, color: Colors.grey),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide.none),
                contentPadding: const EdgeInsets.symmetric(horizontal: 20),
              ),
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 12),
          GestureDetector(
            onTap: _sendMessage,
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: const BoxDecoration(color: Color(0xFF1B4332), shape: BoxShape.circle),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
            ),
          )
        ],
      ),
    );
  }
}
