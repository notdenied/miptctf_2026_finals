<?php

class ResearchController
{
    /**
     * Submit an anomaly for research (creates a task for the Celery worker).
     */
    public static function submit(array $params): void
    {
        $uid  = Session::requireAuth();
        $data = Session::getJsonBody();

        $anomalyId = (int) ($data['anomaly_id'] ?? 0);
        $notes     = trim($data['notes'] ?? '');

        if ($anomalyId <= 0) {
            http_response_code(400);
            echo json_encode(['error' => 'anomaly_id is required']);
            return;
        }

        // Verify anomaly exists and user has clearance
        $db   = Database::getConnection();
        $stmt = $db->prepare('SELECT id, min_clearance, is_private, created_by FROM anomalies WHERE id = ?');
        $stmt->execute([$anomalyId]);
        $anomaly = $stmt->fetch();

        if (!$anomaly) {
            http_response_code(404);
            echo json_encode(['error' => 'Anomaly not found']);
            return;
        }

        if ((int) $anomaly['min_clearance'] > Session::getClearanceLevel()) {
            http_response_code(403);
            echo json_encode(['error' => 'Insufficient clearance level']);
            return;
        }

        if ($anomaly['is_private'] && (int)$anomaly['created_by'] !== $uid) {
            http_response_code(403);
            echo json_encode(['error' => 'Access denied: anomaly is private']);
            return;
        }

        $uuid = Session::uuid();

        $stmt = $db->prepare(
            'INSERT INTO research_tasks (uuid, anomaly_id, researcher_id, status, researcher_notes)
             VALUES (?, ?, ?, ?, ?) RETURNING id, created_at'
        );
        $stmt->execute([$uuid, $anomalyId, $uid, 'PENDING', $notes]);
        $row = $stmt->fetch();

        echo json_encode([
            'id'               => (int) $row['id'],
            'uuid'             => $uuid,
            'anomaly_id'       => $anomalyId,
            'researcher_id'    => $uid,
            'status'           => 'PENDING',
            'researcher_notes' => $notes,
            'created_at'       => $row['created_at'],
        ]);
    }

    /**
     * List current user's research tasks.
     */
    public static function list(array $params): void
    {
        $uid = Session::requireAuth();

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT rt.id, rt.uuid, rt.anomaly_id, rt.status, rt.researcher_notes, rt.created_at, rt.completed_at,
                    a.scp_id, a.title as anomaly_title,
                    ra.uuid as archive_uuid
             FROM research_tasks rt
             JOIN anomalies a ON a.id = rt.anomaly_id
             LEFT JOIN research_archive ra ON ra.task_id = rt.id
             WHERE rt.researcher_id = ?
             ORDER BY rt.created_at DESC'
        );
        $stmt->execute([$uid]);
        $rows = $stmt->fetchAll();

        foreach ($rows as &$r) {
            $r['id']         = (int) $r['id'];
            $r['anomaly_id'] = (int) $r['anomaly_id'];
        }

        echo json_encode($rows);
    }

    /**
     * Get a specific research task by UUID (must be owner).
     */
    public static function get(array $params): void
    {
        $uid  = Session::requireAuth();
        $uuid = $params['uuid'] ?? '';

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT rt.id, rt.uuid, rt.anomaly_id, rt.status, rt.researcher_notes, rt.created_at, rt.completed_at,
                    ra.uuid as archive_uuid, ra.content as archive_content
             FROM research_tasks rt
             LEFT JOIN research_archive ra ON ra.task_id = rt.id
             WHERE rt.uuid = ? AND rt.researcher_id = ?'
        );
        $stmt->execute([$uuid, $uid]);
        $row = $stmt->fetch();

        if (!$row) {
            http_response_code(404);
            echo json_encode(['error' => 'Research task not found']);
            return;
        }

        $row['id']         = (int) $row['id'];
        $row['anomaly_id'] = (int) $row['anomaly_id'];
        echo json_encode($row);
    }
}
