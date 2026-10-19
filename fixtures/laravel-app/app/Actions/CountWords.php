<?php

namespace App\Actions;

class CountWords
{
    public function handle(string $text): int
    {
        $text = trim($text);

        return $text === '' ? 0 : count(preg_split('/\s+/', $text));
    }
}
