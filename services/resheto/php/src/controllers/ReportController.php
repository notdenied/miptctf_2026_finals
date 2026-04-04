<?php

class ReportController
{
    public static function create(array $params): void
    {
        $uid  = Session::requireAuth();
        $data = Session::getJsonBody();

        $title          = trim($data['title'] ?? '');
        $markdown       = $data['content_markdown'] ?? '';
        $anomalyId      = isset($data['anomaly_id']) ? (int) $data['anomaly_id'] : null;
        $classification = trim($data['classification'] ?? 'CONFIDENTIAL');

        if ($title === '' || $markdown === '') {
            http_response_code(400);
            echo json_encode(['error' => 'Title and content_markdown are required']);
            return;
        }

        $validClassifications = ['UNCLASSIFIED', 'CONFIDENTIAL', 'SECRET', 'TOP SECRET', 'LEVEL-5'];
        if (!in_array($classification, $validClassifications, true)) {
            $classification = 'CONFIDENTIAL';
        }

        $uuid = Session::uuid();

        // Convert markdown to HTML
        $parsedown = new Parsedown();
        $htmlBody  = $parsedown->text($markdown);

        // Generate PDF via mPDF
        $pdfPath = null;
        try {
            $mpdf = new \Mpdf\Mpdf([
                'tempDir' => '/tmp/mpdf',
                'mode'    => 'utf-8',
                'format'  => 'A4',
                'default_font' => 'dejavusans',
            ]);

            $cssStyle = '
                body { font-family: DejaVu Sans, sans-serif; color: #222; background: #fff; }
                h1 { color: #8B0000; border-bottom: 2px solid #8B0000; padding-bottom: 8px; }
                h2, h3 { color: #333; }
                .header { text-align: center; margin-bottom: 20px; }
                .header .classification { font-size: 18px; font-weight: bold; color: #C00;
                    border: 3px solid #C00; padding: 5px 20px; display: inline-block; }
                .header .title { font-size: 24px; margin-top: 10px; }
                .footer { text-align: center; font-size: 10px; color: #666; }
                code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
                pre { background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; }
                blockquote { border-left: 4px solid #8B0000; margin: 10px 0; padding: 10px 20px; background: #fff5f5; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                th { background: #f0f0f0; }
            ';

            $html = "
                <style>{$cssStyle}</style>
                <div class='header'>
                    <div class='classification'>⬤ {$classification} ⬤</div>
                    <div class='title'>{$title}</div>
                    <div style='font-size:12px;color:#666;margin-top:5px;'>SCP Foundation — Resheto Containment System</div>
                </div>
                <hr>
                {$htmlBody}
                <hr>
                <div class='footer'>
                    Report UUID: {$uuid} | Generated: " . date('Y-m-d H:i:s') . "
                </div>
            ";

            $mpdf->WriteHTML($html);
            $pdfFilename = $uuid . '.pdf';
            $pdfFullPath = '/var/www/html/storage/pdfs/' . $pdfFilename;
            $mpdf->Output($pdfFullPath, \Mpdf\Output\Destination::FILE);
            $pdfPath = $pdfFilename;
        } catch (\Throwable $e) {
            // PDF generation failed — still save the report
            error_log('mPDF error: ' . $e->getMessage());
        }

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'INSERT INTO reports (uuid, title, content_markdown, pdf_path, author_id, anomaly_id, classification)
             VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id, created_at'
        );
        $stmt->execute([$uuid, $title, $markdown, $pdfPath, $uid, $anomalyId, $classification]);
        $row = $stmt->fetch();

        echo json_encode([
            'id'               => (int) $row['id'],
            'uuid'             => $uuid,
            'title'            => $title,
            'content_markdown' => $markdown,
            'pdf_path'         => $pdfPath,
            'author_id'        => $uid,
            'anomaly_id'       => $anomalyId,
            'classification'   => $classification,
            'created_at'       => $row['created_at'],
        ]);
    }

    public static function list(array $params): void
    {
        $uid = Session::requireAuth();

        $db   = Database::getConnection();
        $stmt = $db->prepare(
            'SELECT id, uuid, title, pdf_path, anomaly_id, classification, created_at
             FROM reports
             WHERE author_id = ?
             ORDER BY created_at DESC'
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
            'SELECT id, uuid, title, content_markdown, pdf_path, author_id, anomaly_id, classification, created_at
             FROM reports WHERE uuid = ? AND author_id = ?'
        );
        $stmt->execute([$uuid, $uid]);
        $row = $stmt->fetch();

        if (!$row) {
            http_response_code(404);
            echo json_encode(['error' => 'Report not found']);
            return;
        }

        $row['id']        = (int) $row['id'];
        $row['author_id'] = (int) $row['author_id'];
        if ($row['anomaly_id']) $row['anomaly_id'] = (int) $row['anomaly_id'];
        echo json_encode($row);
    }

    public static function downloadPdf(array $params): void
    {
        $uid  = Session::requireAuth();
        $uuid = $params['uuid'] ?? '';

        $db   = Database::getConnection();
        $stmt = $db->prepare('SELECT pdf_path FROM reports WHERE uuid = ? AND author_id = ?');
        $stmt->execute([$uuid, $uid]);
        $row = $stmt->fetch();

        if (!$row || !$row['pdf_path']) {
            http_response_code(404);
            echo json_encode(['error' => 'PDF not found']);
            return;
        }

        $fullPath = '/var/www/html/storage/pdfs/' . $row['pdf_path'];
        if (!file_exists($fullPath)) {
            http_response_code(404);
            echo json_encode(['error' => 'PDF file missing']);
            return;
        }

        header('Content-Type: application/pdf');
        header('Content-Disposition: inline; filename="report-' . $uuid . '.pdf"');
        header('Content-Length: ' . filesize($fullPath));
        // Clear any JSON content-type set by the front controller
        readfile($fullPath);
        exit;
    }
}
