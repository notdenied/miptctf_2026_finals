<?php

class IncidentController
{
    public static function create(array $params): void
    {
        $uid  = Session::requireAuth();
        $data = Session::getJsonBody();

        $anomalyId     = isset($data['anomaly_id']) ? (int) $data['anomaly_id'] : null;
        $severity      = trim($data['severity'] ?? '');
        $description   = trim($data['description'] ?? '');
        $responseNotes = trim($data['response_notes'] ?? '');

        if ($severity === '' || $description === '') {
            http_response_code(400);
            echo json_encode(['error' => 'severity and description are required']);
            return;
        }

        $validSeverities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
        if (!in_array($severity, $validSeverities, true)) {
            http_response_code(400);
            echo json_encode(['error' => 'Invalid severity', 'valid' => $validSeverities]);
            return;
        }

        $uuid = Session::uuid();
        $db   = Database::getConnection();

        $stmt = $db->prepare(
            'INSERT INTO incident_logs (uuid, anomaly_id, reporter_id, severity, description, response_notes)
             VALUES (?, ?, ?, ?, ?, ?) RETURNING id, created_at'
        );
        $stmt->execute([$uuid, $anomalyId, $uid, $severity, $description, $responseNotes]);
        $row = $stmt->fetch();

        echo json_encode([
            'id'             => (int) $row['id'],
            'uuid'           => $uuid,
            'anomaly_id'     => $anomalyId,
            'reporter_id'    => $uid,
            'severity'       => $severity,
            'description'    => $description,
            'response_notes' => $responseNotes,
            'created_at'     => $row['created_at'],
        ]);
    }

    public static function list(array $params): void
    {
        $uid = Session::requireAuth();

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT il.id, il.uuid, il.anomaly_id, il.severity, il.description, il.response_notes, il.created_at,
                    a.scp_id, a.title as anomaly_title
             FROM incident_logs il
             LEFT JOIN anomalies a ON a.id = il.anomaly_id
             WHERE il.reporter_id = ?
             ORDER BY il.created_at DESC'
        );
        $stmt->execute([$uid]);
        $rows = $stmt->fetchAll();

        foreach ($rows as &$r) {
            $r['id'] = (int) $r['id'];
            if ($r['anomaly_id']) $r['anomaly_id'] = (int) $r['anomaly_id'];
        }

        echo json_encode($rows);
    }

    public static function get(array $params): void
    {
        $uid  = Session::requireAuth();
        $uuid = $params['uuid'] ?? '';

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT il.id, il.uuid, il.anomaly_id, il.severity, il.description, il.response_notes, il.created_at,
                    a.scp_id, a.title as anomaly_title
             FROM incident_logs il
             LEFT JOIN anomalies a ON a.id = il.anomaly_id
             WHERE il.uuid = ? AND il.reporter_id = ?'
        );
        $stmt->execute([$uuid, $uid]);
        $row = $stmt->fetch();

        if (!$row) {
            http_response_code(404);
            echo json_encode(['error' => 'Incident not found']);
            return;
        }

        $row['id'] = (int) $row['id'];
        if ($row['anomaly_id']) $row['anomaly_id'] = (int) $row['anomaly_id'];
        echo json_encode($row);
    }
}
