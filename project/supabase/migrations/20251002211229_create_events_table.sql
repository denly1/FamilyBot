/*
  # Create events table for event posters

  1. New Tables
    - `events`
      - `id` (uuid, primary key) - Unique identifier for each event
      - `title` (text) - Event title
      - `subtitle` (text) - Event subtitle (e.g., DJ name)
      - `date` (text) - Event date display
      - `time` (text) - Event time display
      - `location` (text) - Venue location
      - `image_url` (text) - URL to event poster image
      - `ticket_url` (text) - URL for ticket purchase
      - `is_active` (boolean) - Whether event is currently displayed
      - `created_at` (timestamptz) - Record creation timestamp
      - `updated_at` (timestamptz) - Record update timestamp

  2. Security
    - Enable RLS on `events` table
    - Add policy for public read access to active events
    - Add policy for authenticated insert/update/delete
*/

CREATE TABLE IF NOT EXISTS events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  subtitle text DEFAULT '',
  date text NOT NULL,
  time text NOT NULL,
  location text NOT NULL,
  image_url text NOT NULL,
  ticket_url text NOT NULL,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view active events"
  ON events
  FOR SELECT
  USING (is_active = true);

CREATE POLICY "Authenticated users can insert events"
  ON events
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Authenticated users can update events"
  ON events
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Authenticated users can delete events"
  ON events
  FOR DELETE
  TO authenticated
  USING (true);