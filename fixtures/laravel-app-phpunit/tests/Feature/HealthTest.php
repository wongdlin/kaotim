<?php

namespace Tests\Feature;

use Tests\TestCase;

class HealthTest extends TestCase
{
    /** AC-2 */
    public function test_ac_2_reports_health_as_json(): void
    {
        $this->getJson('/health')->assertOk()->assertJson(['ok' => true]);
    }
}
