<?php

class AnomalyController
{
    public static function create(array $params): void
    {
        $uid  = Session::requireAuth();
        $data = Session::getJsonBody();

        $scpId       = trim($data['scp_id'] ?? '');
        $objectClass = trim($data['object_class'] ?? '');
        $title       = trim($data['title'] ?? '');
        $description = trim($data['description'] ?? '');
        $containment = trim($data['containment_procedures'] ?? '');
        $minClearance = (int) ($data['min_clearance'] ?? 1);
        $isPrivate   = !empty($data['is_private']);

        if ($scpId === '' || $objectClass === '' || $title === '' || $description === '' || $containment === '') {
            http_response_code(400);
            echo json_encode(['error' => 'All fields are required: scp_id, object_class, title, description, containment_procedures']);
            return;
        }

        $validClasses = ['Safe', 'Euclid', 'Keter', 'Thaumiel', 'Neutralized', 'Apollyon'];
        if (!in_array($objectClass, $validClasses, true)) {
            http_response_code(400);
            echo json_encode(['error' => 'Invalid object class', 'valid' => $validClasses]);
            return;
        }

        $minClearance = max(1, min(5, $minClearance));

        $db = Database::getConnection();

        // Check SCP-ID uniqueness
        $stmt = $db->prepare('SELECT id FROM anomalies WHERE scp_id = ?');
        $stmt->execute([$scpId]);
        if ($stmt->fetch()) {
            http_response_code(409);
            echo json_encode(['error' => 'SCP ID already exists']);
            return;
        }

        $stmt = $db->prepare(
            'INSERT INTO anomalies (scp_id, object_class, title, description, containment_procedures, min_clearance, is_private, created_by)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id, created_at'
        );
        $stmt->execute([$scpId, $objectClass, $title, $description, $containment, $minClearance, $isPrivate ? 'true' : 'false', $uid]);
        $row = $stmt->fetch();

        echo json_encode([
            'id'                     => (int) $row['id'],
            'scp_id'                 => $scpId,
            'object_class'           => $objectClass,
            'title'                  => $title,
            'description'            => $description,
            'containment_procedures' => $containment,
            'min_clearance'          => $minClearance,
            'is_private'             => $isPrivate,
            'created_by'             => $uid,
            'created_at'             => $row['created_at'],
        ]);
    }

    public static function list(array $params): void
    {
        $uid       = Session::requireAuth();
        $clearance = Session::getClearanceLevel();

        $db   = Database::getConnection();
        // Public anomalies within clearance + own private anomalies
        $stmt = $db->prepare(
            'SELECT id, scp_id, object_class, title, description, containment_procedures, min_clearance, is_private, created_by, created_at
             FROM anomalies
             WHERE min_clearance <= ?
               AND (is_private = false OR created_by = ?)
             ORDER BY created_at DESC'
        );
        $stmt->execute([$clearance, $uid]);
        $rows = $stmt->fetchAll();

        foreach ($rows as &$r) {
            $r['id']            = (int) $r['id'];
            $r['min_clearance'] = (int) $r['min_clearance'];
            $r['is_private']    = (bool) $r['is_private'];
            $r['created_by']    = (int) $r['created_by'];
        }

        echo json_encode($rows);
    }

    public static function get(array $params): void
    {
        $uid       = Session::requireAuth();
        $clearance = Session::getClearanceLevel();
        $id        = (int) ($params['id'] ?? 0);

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT id, scp_id, object_class, title, description, containment_procedures, min_clearance, is_private, created_by, created_at
             FROM anomalies WHERE id = ?'
        );
        $stmt->execute([$id]);
        $row = $stmt->fetch();

        if (!$row) {
            http_response_code(404);
            echo json_encode(['error' => 'Anomaly not found']);
            return;
        }

        // Private anomalies only visible to creator
        if ($row['is_private'] && (int) $row['created_by'] !== $uid) {
            http_response_code(404);
            echo json_encode(['error' => 'Anomaly not found']);
            return;
        }

        if ((int) $row['min_clearance'] > $clearance) {
            http_response_code(403);
            echo json_encode(['error' => 'Insufficient clearance level']);
            return;
        }

        $row['id']            = (int) $row['id'];
        $row['min_clearance'] = (int) $row['min_clearance'];
        $row['is_private']    = (bool) $row['is_private'];
        $row['created_by']    = (int) $row['created_by'];
        echo json_encode($row);
    }

    /**
     * Search anomalies by different characteristics.
     */
    public static function search(array $params): void
    {
        $uid = Session::requireAuth();
        $data = Session::getJsonBody();

        $db = Database::getConnection();
        $username = $db->quote(Session::getUsername());

        // Base query: public anomalies OR owned by current user
        $sql = "SELECT a.id, a.scp_id, a.object_class, a.title, a.description, a.containment_procedures,
                       a.min_clearance, a.is_private, a.created_by, a.created_at
                FROM anomalies a
                JOIN staff s ON s.id = a.created_by
                WHERE (a.is_private = false OR s.username = $username)";

        // Allowed search fields
        $allowedFields = [
            'scp_id', 'object_class', 'title', 'min_clearance',
        ];

        $values = [];

        // AND clauses for each provided search field
        foreach ($allowedFields as $field) {
            if (isset($data[$field]) && $data[$field] !== '') {
                $sql .= " AND a.{$field} = ?";
                $values[] = $data[$field];
            }
        }

        // Text search (ILIKE) for description and containment_procedures
        $textFields = ['description', 'containment_procedures'];
        foreach ($textFields as $field) {
            if (isset($data[$field]) && $data[$field] !== '') {
                $sql .= " AND a.{$field} ILIKE ?";
                $values[] = '%' . $data[$field] . '%';
            }
        }

        $sql .= " ORDER BY a.created_at DESC LIMIT 50";

        $stmt = $db->prepare($sql);
        $stmt->execute($values);
        $rows = $stmt->fetchAll();

        foreach ($rows as &$r) {
            $r['id']            = (int) $r['id'];
            $r['min_clearance'] = (int) $r['min_clearance'];
            $r['is_private']    = (bool) $r['is_private'];
            $r['created_by']    = (int) $r['created_by'];
        }

        echo json_encode($rows);
    }
}
