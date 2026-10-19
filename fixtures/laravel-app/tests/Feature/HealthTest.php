<?php

it('AC-2: reports health as JSON', function () {
    $this->getJson('/health')->assertOk()->assertJson(['ok' => true]);
});
