import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/sensor_provider.dart';

class SleepReportScreen extends StatelessWidget {
  const SleepReportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final sensor = context.watch<SensorProvider>();

    final movementData = sensor.hourlyMovement;

    int maxCount = 1;

    for (final item in movementData) {
      final count = item['count'];

      if (count is num && count.toInt() > maxCount) {
        maxCount = count.toInt();
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('수면 리포트'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              '오늘의 수면 요약',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    const Text(
                      '총 측정 시간',
                      style: TextStyle(fontSize: 16),
                    ),

                    const SizedBox(height: 8),

                    Text(
                      sensor.totalMeasuredLabel,
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 12),

            Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    title: '침상 이탈',
                    value: '${sensor.bedExits}회',
                    icon: Icons.bed_outlined,
                  ),
                ),

                const SizedBox(width: 10),

                Expanded(
                  child: _SummaryCard(
                    title: '평균 심박수',
                    value: sensor.sleepHeartRate == null
                        ? '--'
                        : '${sensor.sleepHeartRate} bpm',
                    icon: Icons.favorite,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    title: '평균 호흡수',
                    value: sensor.sleepBreathRate == null
                        ? '--'
                        : '${sensor.sleepBreathRate} 회/분',
                    icon: Icons.air,
                  ),
                ),

                const SizedBox(width: 10),

                Expanded(
                  child: _SummaryCard(
                    title: '데이터 수집률',
                    value:
                    '${(sensor.dataCoverage * 100).toStringAsFixed(0)}%',
                    icon: Icons.analytics_outlined,
                  ),
                ),
              ],
            ),

            if (sensor.dataCoverage < 0.5) ...[
              const SizedBox(height: 12),

              const Card(
                child: Padding(
                  padding: EdgeInsets.all(14),
                  child: Row(
                    children: [
                      Icon(
                        Icons.info_outline,
                        size: 24,
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          '데이터가 부족해 리포트 정확도가 낮을 수 있습니다.',
                          style: TextStyle(
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],

            const SizedBox(height: 24),

            const Text(
              '시간대별 뒤척임',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            if (movementData.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(
                  vertical: 30,
                ),
                child: Center(
                  child: Text(
                    '뒤척임 데이터가 없습니다.',
                    style: TextStyle(
                      fontSize: 16,
                    ),
                  ),
                ),
              )
            else
              ...movementData.map((data) {
                final hour = data['hour'];
                final countValue = data['count'];

                final count = countValue is num
                    ? countValue.toInt()
                    : 0;

                final hourText = hour is num
                    ? '${hour.toInt().toString().padLeft(2, '0')}시'
                    : '--';

                return Padding(
                  padding: const EdgeInsets.only(
                    bottom: 12,
                  ),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 45,
                        child: Text(hourText),
                      ),

                      Expanded(
                        child: LinearProgressIndicator(
                          value: maxCount == 0
                              ? 0
                              : count / maxCount,
                          minHeight: 18,
                        ),
                      ),

                      const SizedBox(width: 12),

                      Text('$count회'),
                    ],
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;

  const _SummaryCard({
    required this.title,
    required this.value,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: 10,
          vertical: 16,
        ),
        child: Column(
          children: [
            Icon(
              icon,
              size: 26,
            ),

            const SizedBox(height: 8),

            Text(
              title,
              style: const TextStyle(
                fontSize: 13,
              ),
            ),

            const SizedBox(height: 6),

            Text(
              value,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}