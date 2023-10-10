ALTER TABLE suggestion ADD COLUMN upvotes JSON DEFAULT '[]';
ALTER TABLE suggestion ADD COLUMN downvotes JSON DEFAULT '[]';
