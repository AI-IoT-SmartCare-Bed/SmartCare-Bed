import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/sensor_provider.dart';

class AlertScreen extends StatelessWidget {
  const AlertScreen({super.key});

  IconData _getIcon(String severity) {
    switch (severity) {
      case 'danger':
        return Icons.error;
      case 'warning':
        return Icons.warning_amber_rounded;
      case 'caution':
        return Icons.info_outline;
      default:
        return Icons.check_circle_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final sensor = context.watch<SensorProvider>();
    final events = sensor.serverEvents;

    return Scaffold(
      appBar: AppBar(
        title: const Text('알림 내역'),
        centerTitle: true,
      ),
      body: events.isEmpty
          ? const Center(
        child: Text(
          '아직 알림이 없습니다.',
          style: TextStyle(fontSize: 18),
        ),
      )
          : RefreshIndicator(
        onRefresh: sensor.fetchEvents,
        child: ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: events.length,
          separatorBuilder: (context, index) =>
          const SizedBox(height: 12),
          itemBuilder: (context, index) {
            final event = events[index];

            final title =
                event['title']?.toString() ?? '알림';

            final message =
            event['message']?.toString();

            final timeLabel =
                event['time_label']?.toString() ?? '';

            final severity =
                event['severity']?.toString() ?? 'normal';

            final status =
                event['status']?.toString() ?? '';

            return Card(
              child: ListTile(
                leading: Icon(
                  _getIcon(severity),
                  size: 32,
                ),
                title: Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),

                    if (status == 'active')
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          color: Colors.red.withValues(
                            alpha: 0.1,
                          ),
                        ),
                        child: const Text(
                          '미확인',
                          style: TextStyle(
                            fontSize: 11,
                          ),
                        ),
                      ),
                  ],
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    [
                      if (message != null &&
                          message.isNotEmpty)
                        message,
                      if (timeLabel.isNotEmpty)
                        timeLabel,
                    ].join('\n'),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}