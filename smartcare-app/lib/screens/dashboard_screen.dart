import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/sensor_provider.dart';
import '../widgets/sensor_card.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final sensor = context.watch<SensorProvider>();

    final bool isOccupied = sensor.occupancyState == 'occupied';
    final bool isEmpty = sensor.occupancyState == 'empty';

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          '스마트 케어 보호자',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              '현재 상태',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 10),

            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 16,
                ),
                child: Row(
                  children: [
                    Icon(
                      isOccupied
                          ? Icons.bed
                          : isEmpty
                          ? Icons.bed_outlined
                          : Icons.hourglass_empty,
                      size: 36,
                    ),

                    const SizedBox(width: 16),

                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            sensor.occupancyLabel,
                            style: const TextStyle(
                              fontSize: 19,
                              fontWeight: FontWeight.bold,
                            ),
                          ),

                          const SizedBox(height: 3),

                          Text(
                            sensor.occupancyDurationLabel ??
                                (isOccupied
                                    ? '환자가 침대에 위치해 있습니다.'
                                    : isEmpty
                                    ? '환자가 침대에 있지 않습니다.'
                                    : '환자 위치 정보를 확인하고 있습니다.'),
                            style: const TextStyle(
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // =========================
            // 오늘의 케어 조언
            // =========================

            const SizedBox(height: 20),

            const Text(
              '오늘의 케어 조언',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 10),

            if (sensor.advices.isEmpty && sensor.notices.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    '현재 제공되는 케어 조언이 없습니다.',
                    style: TextStyle(
                      fontSize: 14,
                    ),
                  ),
                ),
              ),

            ...sensor.advices.map(
                  (advice) {
                final text =
                    advice['text']?.toString() ?? '케어 조언 내용이 없습니다.';

                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.lightbulb_outline,
                          size: 26,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            text,
                            style: const TextStyle(
                              fontSize: 14,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),

            ...sensor.notices.map(
                  (notice) {
                final text =
                    notice['text']?.toString() ?? '안내 내용이 없습니다.';

                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.info_outline,
                          size: 26,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            text,
                            style: const TextStyle(
                              fontSize: 14,
                              height: 1.4,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),

            const SizedBox(height: 20),

            const Text(
              '실시간 건강 정보',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 10),

            SensorCard(
              title: '심박수',
              value: sensor.heartRateStale
                  ? '측정 중…'
                  : sensor.heartRate?.toString() ?? '--',
              unit: sensor.heartRateStale ? '' : 'bpm',
              icon: Icons.favorite,
            ),

            SensorCard(
              title: '호흡수',
              value: sensor.respirationRateStale
                  ? '측정 중…'
                  : sensor.respirationRate?.toString() ?? '--',
              unit: sensor.respirationRateStale ? '' : '회/분',
              icon: Icons.air,
            ),

            SensorCard(
              title: '위험도',
              value: sensor.riskLevel,
              unit: '',
              icon: Icons.health_and_safety,
            ),

            if (!sensor.deviceOnline) ...[
              const SizedBox(height: 10),

              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.cloud_off,
                        size: 26,
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text(
                          '침대 센서 연결이 끊겨 있습니다.',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}