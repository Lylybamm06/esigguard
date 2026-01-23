-- Script SQL à exécuter dans Azure SQL Database

-- Supprimer les tables si elles existent
IF OBJECT_ID('attachments', 'U') IS NOT NULL 
    DROP TABLE attachments;
GO

IF OBJECT_ID('emails', 'U') IS NOT NULL 
    DROP TABLE emails;
GO

-- Créer la table emails
CREATE TABLE emails (
    id INT IDENTITY(1,1) PRIMARY KEY,
    sender_address NVARCHAR(255),
    sender_name NVARCHAR(255),
    domain NVARCHAR(255),
    subject NVARCHAR(500),
    body_snippet NVARCHAR(MAX),
    urls NVARCHAR(MAX),
    timestamp NVARCHAR(50),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    
    INDEX idx_sender (sender_address),
    INDEX idx_domain (domain),
    INDEX idx_created_at (created_at)
);
GO

-- Créer la table attachments (pièces jointes)
CREATE TABLE attachments (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email_id INT NOT NULL,
    filename NVARCHAR(255) NOT NULL,
    extension NVARCHAR(50),
    content_type NVARCHAR(100),
    size BIGINT,
    hash NVARCHAR(255),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    INDEX idx_email_id (email_id),
    INDEX idx_extension (extension)
);
GO

-- Vue pour voir les emails récents avec le nombre de pièces jointes
CREATE VIEW recent_emails_with_attachments AS
SELECT 
    e.id,
    e.sender_address,
    e.sender_name,
    e.domain,
    e.subject,
    LEFT(e.body_snippet, 100) as body_preview,
    e.created_at,
    COUNT(a.id) as attachment_count
FROM emails e
LEFT JOIN attachments a ON e.id = a.email_id
GROUP BY e.id, e.sender_address, e.sender_name, e.domain, e.subject, e.body_snippet, e.created_at;
GO

-- Vue pour voir toutes les pièces jointes
CREATE VIEW all_attachments AS
SELECT 
    a.id,
    a.email_id,
    e.sender_address,
    e.subject,
    a.filename,
    a.extension,
    a.content_type,
    a.size,
    a.created_at
FROM attachments a
JOIN emails e ON a.email_id = e.id;
GO

