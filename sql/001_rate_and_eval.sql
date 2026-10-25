CREATE SCHEMA hf;
GO

CREATE TABLE hf.RateCard (
    RoleName nvarchar(40) NOT NULL PRIMARY KEY,
    HourlyUsd int NOT NULL
);

CREATE TABLE hf.Account (
    AccountCode nvarchar(20) NOT NULL PRIMARY KEY,
    AccountName nvarchar(100) NOT NULL,
    DiscountPercent decimal(5, 2) NOT NULL
);

CREATE TABLE hf.Quote (
    IdempotencyKey nvarchar(100) NOT NULL PRIMARY KEY,
    QuoteId uniqueidentifier NOT NULL,
    AccountCode nvarchar(20) NOT NULL,
    RoleName nvarchar(40) NOT NULL,
    Hours int NOT NULL,
    AmountUsd decimal(18, 2) NOT NULL,
    PayloadJson nvarchar(max) NOT NULL,
    CreatedAt datetime2 NOT NULL CONSTRAINT DF_Quote_CreatedAt DEFAULT SYSUTCDATETIME()
);

CREATE TABLE hf.EvalResult (
    CaseId nvarchar(20) NOT NULL PRIMARY KEY,
    Outcome nvarchar(40) NOT NULL,
    Passed bit NOT NULL,
    LatencyMs int NULL,
    Tokens int NULL,
    CostUsd decimal(18, 4) NULL,
    RecordedAt datetime2 NOT NULL CONSTRAINT DF_EvalResult_RecordedAt DEFAULT SYSUTCDATETIME()
);
GO

INSERT INTO hf.RateCard (RoleName, HourlyUsd) VALUES
    ('consultant', 180),
    ('senior', 240),
    ('principal', 320);

INSERT INTO hf.Account (AccountCode, AccountName, DiscountPercent) VALUES
    ('NORTH', 'Northline', 0),
    ('BRIGHT', 'Brightwater', 10);
GO
