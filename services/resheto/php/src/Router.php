<?php

/**
 * Minimal request router with named parameters.
 */
class Router
{
    private array $routes = [];

    public function get(string $pattern, array $handler): void
    {
        $this->routes[] = ['GET', $pattern, $handler];
    }

    public function post(string $pattern, array $handler): void
    {
        $this->routes[] = ['POST', $pattern, $handler];
    }

    public function dispatch(): void
    {
        $method = $_SERVER['REQUEST_METHOD'];
        $uri    = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

        // Handle CORS preflight
        if ($method === 'OPTIONS') {
            header('Access-Control-Allow-Origin: *');
            header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
            header('Access-Control-Allow-Headers: Content-Type');
            http_response_code(204);
            return;
        }

        foreach ($this->routes as [$routeMethod, $pattern, $handler]) {
            if ($method !== $routeMethod) {
                continue;
            }

            $regex = preg_replace('/\{(\w+)\}/', '(?P<$1>[^/]+)', $pattern);
            $regex = '#^' . $regex . '$#';

            if (preg_match($regex, $uri, $matches)) {
                $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
                try {
                    call_user_func($handler, $params);
                } catch (Throwable $e) {
                    http_response_code(500);
                    echo json_encode([
                        'error'   => 'Internal server error',
                        'message' => $e->getMessage(),
                    ]);
                }
                return;
            }
        }

        http_response_code(404);
        echo json_encode(['error' => 'Not found', 'path' => $uri]);
    }
}
