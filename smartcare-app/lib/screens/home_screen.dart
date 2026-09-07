import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/sensor_provider.dart';
import 'alert_screen.dart';
import 'dashboard_screen.dart';
import 'sleep_report_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int selectedIndex = 0;

  Timer? refreshTimer;

  final List<Widget> screens = const [
    DashboardScreen(),
    AlertScreen(),
    SleepReportScreen(),
  ];

  @override
  void initState() {
    super.initState();

    // 앱 시작 시 바로 서버 데이터 불러오기
    Future.microtask(() async {
      final sensor = context.read<SensorProvider>();

      await sensor.fetchLatestData();
      await sensor.fetchAdvice();
      await sensor.fetchEvents();
      await sensor.fetchSleepData();
    });

    // 이후 5초마다 서버 데이터 새로 불러오기
    refreshTimer = Timer.periodic(
      const Duration(seconds: 5),
          (timer) async {
        if (!mounted) return;

        final sensor = context.read<SensorProvider>();

        await sensor.fetchLatestData();
        await sensor.fetchAdvice();
        await sensor.fetchEvents();
        await sensor.fetchSleepData();
      },
    );
  }

  void changeScreen(int index) {
    setState(() {
      selectedIndex = index;
    });
  }

  @override
  void dispose() {
    refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: screens[selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: selectedIndex,
        onDestinationSelected: changeScreen,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: '대시보드',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_none),
            selectedIcon: Icon(Icons.notifications),
            label: '알림',
          ),
          NavigationDestination(
            icon: Icon(Icons.bedtime_outlined),
            selectedIcon: Icon(Icons.bedtime),
            label: '수면 리포트',
          ),
        ],
      ),
    );
  }
}