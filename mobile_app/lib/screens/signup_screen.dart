import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/api_service.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _apiService = ApiService();
  String _selectedLanguage = 'en';
  bool _isLoading = false;
  String? _errorMessage;

  final Map<String, String> _languages = {
    'en': 'English',
    'hi': 'हिन्दी (Hindi)',
    'ml': 'മലയാളം (Malayalam)',
    'ta': 'தமிழ் (Tamil)',
    'te': 'తెలుగు (Telugu)',
    'kn': 'ಕನ್ನಡ (Kannada)',
  };

  Future<void> _handleSignup() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final success = await _apiService.signup(
        name: _nameController.text,
        phone: _phoneController.text,
        password: _passwordController.text,
        language: _selectedLanguage,
      );

      if (success) {
        if (mounted) {
          // After signup, automatically login or redirect to dashboard
          Navigator.pushReplacementNamed(context, '/');
        }
      } else {
        setState(() =>
            _errorMessage = 'Signup failed. Phone number might already exist.');
      }
    } catch (e) {
      setState(() =>
          _errorMessage = 'Connection error. Check if server is running.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      body: Stack(
        children: [
          // Background Gradient/Pattern
          Positioned(
            top: -50,
            left: -50,
            child: Opacity(
              opacity: 0.05,
              child: Icon(Icons.park, size: 300, color: Color(0xFF1B4332)),
            ),
          ),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 20),
              child: Column(
                children: [
                  const SizedBox(height: 20),

                  // Logo/Icon
                  Container(
                    width: 70,
                    height: 70,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF2D6A4F), Color(0xFF40916C)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(22),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF1B4332).withOpacity(0.2),
                          blurRadius: 15,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.person_add_alt_1,
                        size: 35, color: Colors.white),
                  ),

                  const SizedBox(height: 25),

                  Text(
                    'Create Your Legacy',
                    style: GoogleFonts.outfit(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: const Color(0xFF1B4332),
                    ),
                  ),

                  const SizedBox(height: 8),

                  Text(
                    "Begin your journey with Sakhi.\nLet's grow together.",
                    textAlign: TextAlign.center,
                    style: GoogleFonts.outfit(
                      fontSize: 15,
                      color: const Color(0xFF1B4332).withOpacity(0.6),
                    ),
                  ),

                  const SizedBox(height: 35),

                  // Signup Form Card
                  Container(
                    padding: const EdgeInsets.all(25),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.8),
                      borderRadius: BorderRadius.circular(35),
                      border: Border.all(color: Colors.white),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.04),
                          blurRadius: 25,
                          offset: const Offset(0, 12),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (_errorMessage != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 15),
                            child: Text(
                              _errorMessage!,
                              style: const TextStyle(
                                  color: Colors.red, fontSize: 13),
                            ),
                          ),
                        _buildLabel('FULL NAME'),
                        TextField(
                          controller: _nameController,
                          decoration: _inputDecoration(
                              Icons.person_outline, 'Your Name'),
                        ),
                        const SizedBox(height: 20),
                        _buildLabel('PHONE NUMBER'),
                        TextField(
                          controller: _phoneController,
                          keyboardType: TextInputType.phone,
                          decoration: _inputDecoration(
                              Icons.phone_outlined, '10-digit number'),
                        ),
                        const SizedBox(height: 20),
                        _buildLabel('SECURITY PASSWORD'),
                        TextField(
                          controller: _passwordController,
                          obscureText: true,
                          decoration: _inputDecoration(
                              Icons.lock_outline, 'Create password'),
                        ),
                        const SizedBox(height: 20),
                        _buildLabel('NATIVE LANGUAGE'),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 15),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                                color:
                                    const Color(0xFF1B4332).withOpacity(0.1)),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              value: _selectedLanguage,
                              isExpanded: true,
                              icon: const Icon(Icons.keyboard_arrow_down,
                                  color: Color(0xFF1B4332)),
                              items: _languages.entries.map((e) {
                                return DropdownMenuItem(
                                  value: e.key,
                                  child: Text(e.value,
                                      style: GoogleFonts.outfit(fontSize: 15)),
                                );
                              }).toList(),
                              onChanged: (val) =>
                                  setState(() => _selectedLanguage = val!),
                            ),
                          ),
                        ),
                        const SizedBox(height: 35),
                        SizedBox(
                          width: double.infinity,
                          height: 58,
                          child: ElevatedButton(
                            onPressed: _isLoading ? null : _handleSignup,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF1B4332),
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(18),
                              ),
                              elevation: 4,
                            ),
                            child: _isLoading
                                ? const CircularProgressIndicator(
                                    color: Colors.white)
                                : Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Text(
                                        'Plant Your Seed (Join)',
                                        style: GoogleFonts.outfit(
                                          fontSize: 17,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Icon(Icons.eco, size: 20),
                                    ],
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 25),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        "Already have an account? ",
                        style: GoogleFonts.outfit(
                            color: const Color(0xFF1B4332).withOpacity(0.6)),
                      ),
                      TextButton(
                        onPressed: () {
                          Navigator.pushNamed(context, '/login');
                        },
                        child: const Text(
                          'Log in to your Farm',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1B4332),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, left: 5),
      child: Text(
        text,
        style: GoogleFonts.outfit(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: const Color(0xFF1B4332).withOpacity(0.4),
          letterSpacing: 1.2,
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(IconData icon, String hint) {
    return InputDecoration(
      prefixIcon:
          Icon(icon, color: const Color(0xFF1B4332).withOpacity(0.3), size: 22),
      hintText: hint,
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(vertical: 18, horizontal: 15),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: BorderSide(color: const Color(0xFF1B4332).withOpacity(0.1)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: BorderSide(color: const Color(0xFF1B4332).withOpacity(0.1)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: Color(0xFF1B4332)),
      ),
    );
  }
}
