CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  tg_id BIGINT UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  phone TEXT,
  locale VARCHAR(5) DEFAULT 'uz',
  created_at TIMESTAMPTZ DEFAULT now()
);
Sardoba (5-mkr)
Sardoba (Geofizika)
Sardoba (Gijduvon)
Sardoba (Severniy)
Sardoba (5-мкр)
Sardoba (Геофизика)
Sardoba (Гиждуван)
Sardoba (Северный)
CREATE TABLE IF NOT EXISTS branches (
  id BIGSERIAL PRIMARY KEY,
  nameuz TEXT NOT NULL,
  nameru TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reviews (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  branch_id SMALLINT REFERENCES branches(id) ON DELETE CASCADE,
  rating SMALLINT CHECK (rating BETWEEN 1 AND 5),  
  text TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS review_photos (
  id BIGSERIAL PRIMARY KEY,
  review_id BIGINT REFERENCES reviews(id) ON DELETE CASCADE,
  file_id TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS admins (
  id BIGSERIAL PRIMARY KEY,
  tg_id BIGINT UNIQUE NOT NULL,
  group_id BIGINT,
  role VARCHAR(20) NOT NULL CHECK (role IN ('admin','super_admin')),
  created_at TIMESTAMPTZ DEFAULT now()
);
