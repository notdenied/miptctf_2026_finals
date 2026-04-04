<?php

/**
 * Internal endpoints
 */
class InternalController
{
    /**
     * Health check.
     */
    public static function health(array $params): void
    {
        echo json_encode(['status' => 'ok', 'service' => 'resheto']);
    }

    /**
     * Get next pending research tasks for the worker.
     */
    public static function pendingResearch(array $params): void
    {
        $db   = Database::getConnection();
        $stmt = $db->prepare(
            "SELECT id, uuid, anomaly_id, researcher_id, researcher_notes, status
             FROM research_tasks
             WHERE status IN ('PENDING', 'PROCESSING')
             ORDER BY created_at ASC"
        );
        $stmt->execute();
        $rows = $stmt->fetchAll();

        if (empty($rows)) {
            http_response_code(204);
            return;
        }

        // Mark PENDING as PROCESSING
        $update = $db->prepare("UPDATE research_tasks SET status = 'PROCESSING' WHERE id = ? AND status = 'PENDING'");
        foreach ($rows as &$row) {
            $update->execute([$row['id']]);
            $row['id']            = (int) $row['id'];
            $row['anomaly_id']    = (int) $row['anomaly_id'];
            $row['researcher_id'] = (int) $row['researcher_id'];
        }

        echo json_encode($rows);
    }

    /**
     * Worker uploads completed research result.
     */
    public static function completeResearch(array $params): void
    {
        $uuid = $params['uuid'] ?? '';
        $data = Session::getJsonBody();
        $content = $data['content'] ?? '';

        if ($content === '') {
            http_response_code(400);
            echo json_encode(['error' => 'content is required']);
            return;
        }

        $db = Database::getConnection();

        // Find the task
        $stmt = $db->prepare('SELECT id, researcher_id FROM research_tasks WHERE uuid = ?');
        $stmt->execute([$uuid]);
        $task = $stmt->fetch();

        if (!$task) {
            http_response_code(404);
            echo json_encode(['error' => 'Task not found']);
            return;
        }

        $stmt = $db->prepare('SELECT uuid FROM research_archive WHERE task_id = ?');
        $stmt->execute([$task['id']]);
        $existing = $stmt->fetch();

        if ($existing) {
            $archiveUuid = $existing['uuid'];
            $stmt = $db->prepare('UPDATE research_archive SET content = ?, created_at = NOW() WHERE task_id = ?');
            $stmt->execute([$content, $task['id']]);
        } else {
            $archiveUuid = Session::uuid();
            $stmt = $db->prepare(
                'INSERT INTO research_archive (uuid, task_id, researcher_id, content)
                 VALUES (?, ?, ?, ?)'
            );
            $stmt->execute([$archiveUuid, $task['id'], $task['researcher_id'], $content]);
        }

        // Mark task as done
        $stmt = $db->prepare('UPDATE research_tasks SET status = ?, completed_at = NOW() WHERE uuid = ?');
        $stmt->execute(['DONE', $uuid]);

        echo json_encode([
            'ok'           => true,
            'archive_uuid' => $archiveUuid,
        ]);
    }

    /**
     * Get research result content by task UUID.
     */
    public static function getResearchResult(array $params): void
    {
        $uuid = $params['uuid'] ?? '';

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT ra.uuid as archive_uuid, ra.content, ra.created_at,
                    rt.uuid as task_uuid, rt.researcher_notes, rt.status
             FROM research_archive ra
             JOIN research_tasks rt ON rt.id = ra.task_id
             WHERE rt.uuid = ?'
        );
        $stmt->execute([$uuid]);
        $row = $stmt->fetch();

        if (!$row) {
            http_response_code(404);
            echo json_encode(['error' => 'Research result not found']);
            return;
        }

        echo json_encode($row);
    }

    /**
     * Get anomaly information by ID (called by worker during processing).
     */
    public static function getAnomalyInfo(array $params): void
    {
        $id = $params['id'] ?? '';

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT id, scp_id, title, description, containment_procedures, object_class, is_private
             FROM anomalies
             WHERE id = ?'
        );
        $stmt->execute([$id]);
        $anomaly = $stmt->fetch();

        if (!$anomaly) {
            http_response_code(404);
            echo json_encode(['error' => 'Anomaly not found']);
            return;
        }

        echo json_encode($anomaly);
    }
}
