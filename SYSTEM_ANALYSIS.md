# FIMS System Analysis & Architecture

## System Architecture Diagram

```mermaid
graph TB
    subgraph "Client Browser"
        USER[User Browser]
    end

    subgraph "Vercel Serverless Platform"
        VR[Vercel Router<br/>vercel.json]
        API[api/index.py<br/>Serverless Function Entry]
        
        subgraph "Flask Application - app.py"
            FLASK[Flask App Instance]
            LM[Flask-Login Manager]
            
            subgraph "Route Groups"
                AUTH[Auth Routes<br/>/login /logout /]
                ADMIN[Admin Routes<br/>/admin/*]
                RP[RakePoint Routes<br/>/rakepoint/*]
                WH[Warehouse Routes<br/>/warehouse/*]
                ACC[Accountant Routes<br/>/accountant/*]
                API_EP[API Endpoints<br/>/api/*]
            end
        end
        
        subgraph "Database Layer - database.py"
            DB[Database Class]
            CACHE[SimpleCache<br/>TTL=300s]
            CONN[Connection Pool<br/>Reuse cloud conn]
        end
    end

    subgraph "Turso Cloud DB"
        TURSO[(Turso LibSQL<br/>AWS AP-South-1)]
    end

    USER -->|HTTPS| VR
    VR -->|"/(.*)"| API
    API -->|imports| FLASK
    FLASK --> LM
    LM --> AUTH
    FLASK --> ADMIN
    FLASK --> RP
    FLASK --> WH
    FLASK --> ACC
    FLASK --> API_EP
    
    AUTH --> DB
    ADMIN --> DB
    RP --> DB
    WH --> DB
    ACC --> DB
    API_EP --> DB
    
    DB --> CACHE
    DB --> CONN
    CONN -->|libsql TCP/TLS| TURSO
```

## Cold Start Request Flow (Login Page)

```mermaid
sequenceDiagram
    participant B as Browser
    participant V as Vercel Edge
    participant L as Lambda (Python)
    participant F as Flask App
    participant D as Database
    participant T as Turso Cloud DB

    Note over V: Cold Start Begins
    B->>V: GET /login
    V->>L: Route to api/index.py
    
    rect rgb(255, 235, 235)
        Note over L: BEFORE FIX: ~7-9s total
        L->>L: Import Flask + deps (~0.5s)
        L->>L: Import reportlab via reports.py (~0.1s)
        L->>L: Create Flask app
        L->>D: Database() constructor
        D->>T: TCP/TLS connect (~1-2s)
        D->>T: SELECT 1 (test) (~0.3s)
        D->>T: 15x CREATE TABLE IF NOT EXISTS (~3-5s!)
        D->>T: 4x SELECT COUNT(*) defaults (~0.5s)
        D->>T: 6x PRAGMA table_info or fallback (~1-2s)
        D->>T: 19x ALTER TABLE migrations (~2-4s)
    end
    
    rect rgb(235, 255, 235)
        Note over L: AFTER FIX: ~2-3s total
        L->>L: Import Flask + deps (~0.5s)
        L->>L: No reportlab import (removed)
        L->>L: Create Flask app
        L->>D: Database() constructor
        D->>T: TCP/TLS connect (~1-2s)
        D->>T: SELECT 1 (test) (~0.3s)
        D-->>D: Skip schema init (cloud)
    end
    
    F->>B: render login.html
    
    Note over B: User submits credentials
    B->>F: POST /login
    F->>D: authenticate_user()
    D->>T: SELECT * FROM users WHERE username=?
    D->>F: user row
    F->>F: check_password_hash()
    F->>B: 302 Redirect to /admin/dashboard
```

## Admin Dashboard Data Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as Flask /admin/dashboard
    participant D as Database
    participant C as Cache (TTL=300s)
    participant T as Turso DB

    B->>F: GET /admin/dashboard
    F->>D: get_dashboard_stats_optimized()
    D->>C: Check cache key
    
    alt Cache HIT
        C-->>D: Return cached stats
    else Cache MISS
        D->>T: Single SELECT with 8 subqueries
        T-->>D: Row with all counts
        D->>C: Store in cache
    end
    
    D-->>F: stats dict

    F->>D: get_total_shortage()
    D->>T: SELECT SUM(shortage) FROM rakes
    D-->>F: shortage value

    F->>D: get_rakes_with_balances(limit=5)
    D->>C: Check cache
    alt Cache MISS
        D->>T: Single SELECT with 2 correlated subqueries
        T-->>D: 5 rake rows
        D->>C: Store
    end
    D-->>F: recent_rakes list

    F->>D: get_daywise_warehouse_stock(days=7)
    D->>T: SELECT with GROUP BY DATE
    D->>D: Fill missing dates with 0
    D-->>F: 7-day stock list

    F->>B: Render dashboard.html<br/>(day-wise table, rakes table, stat cards)
```

## Role-Based Access Control

```mermaid
graph LR
    subgraph "User Roles"
        A[Admin]
        R[RakePoint]
        W[Warehouse]
        AC[Accountant]
    end

    subgraph "Admin Capabilities"
        A1[Add/Close/Reopen Rakes]
        A2[View All Reports]
        A3[Manage Accounts/Products]
        A4[Warehouse Stock Management]
        A5[Excel Downloads]
        A6[Logistic Bill Summary]
        A7[Manage Users & Warehouses]
    end

    subgraph "RakePoint Capabilities"
        R1[Create Loading Slips]
        R2[Create Builties]
        R3[View Active Rakes]
        R4[View Own Loading Slips]
    end

    subgraph "Warehouse Capabilities"
        W1[Stock IN Recording]
        W2[Stock OUT Recording]
        W3[Create Warehouse Builties]
        W4[DO Creation]
        W5[View Balance]
    end

    subgraph "Accountant Capabilities"
        AC1[Create E-Bills]
        AC2[Upload Bill/Eway PDFs]
        AC3[View All Builties for Billing]
    end

    A --> A1 & A2 & A3 & A4 & A5 & A6 & A7
    R --> R1 & R2 & R3 & R4
    W --> W1 & W2 & W3 & W4 & W5
    AC --> AC1 & AC2 & AC3
```

## Database Entity Relationship

```mermaid
erDiagram
    users {
        int user_id PK
        text username UK
        text password_hash
        text role
    }
    
    rakes {
        int rake_id PK
        text rake_code UK
        text company_name
        real rr_quantity
        text product_name
        int is_closed
        real shortage
    }
    
    loading_slips {
        int slip_id PK
        text rake_code FK
        int account_id FK
        int warehouse_id FK
        real quantity_mt
        int truck_id FK
    }
    
    builty {
        int builty_id PK
        text builty_number UK
        text rake_code FK
        int account_id FK
        int warehouse_id FK
        int truck_id FK
        real quantity_mt
        real total_freight
    }
    
    warehouse_stock {
        int stock_id PK
        int warehouse_id FK
        text transaction_type
        real quantity_mt
        text source_type
        date date
    }
    
    ebills {
        int ebill_id PK
        int builty_id FK
        text ebill_number UK
        real amount
        text bill_pdf
        text eway_bill_pdf
    }
    
    accounts {
        int account_id PK
        text account_name
        text account_type
    }
    
    warehouses {
        int warehouse_id PK
        text warehouse_name
        text location
        real capacity
    }
    
    trucks {
        int truck_id PK
        text truck_number UK
        text driver_name
    }

    rakes ||--o{ loading_slips : "dispatched via"
    rakes ||--o{ builty : "delivered via"
    loading_slips }o--|| accounts : "to"
    loading_slips }o--|| warehouses : "to"
    loading_slips }o--|| trucks : "transported by"
    builty }o--|| accounts : "for"
    builty }o--|| warehouses : "to"
    builty }o--|| trucks : "transported by"
    builty ||--o| ebills : "billed as"
    warehouses ||--o{ warehouse_stock : "tracks"
```

## Vercel Timeout Risk Map

```mermaid
graph TB
    subgraph "🟢 Safe Routes < 3s"
        S1[GET /login]
        S2[POST /login]
        S3[GET /admin/dashboard]
        S4[GET /rakepoint/create-builty]
        S5[GET /warehouse/stock-in]
        S6[GET /accountant/create-ebill]
        S7[GET /api/next-lr-number]
    end

    subgraph "🟡 At Risk 3-8s"
        W1[GET /rakepoint/dashboard<br/>4 DB queries + filtering]
        W2[GET /warehouse/dashboard<br/>4 sequential large queries]
        W3[GET /accountant/dashboard<br/>Multiple get_all + loops]
        W4[GET /admin/warehouse-summary<br/>3 complex GROUP BY queries]
        W5[GET /admin/logistic-bill<br/>Complex JOIN query]
    end

    subgraph "🔴 High Risk > 8s"
        D1[GET /admin/download-*-excel<br/>9 Excel generation routes<br/>Heavy openpyxl + large queries]
        D2[GET /warehouse/balance<br/>N+1 loop per warehouse]
        D3[POST /accountant/create-ebill<br/>File upload + DB writes]
    end

    style S1 fill:#90EE90
    style S2 fill:#90EE90
    style S3 fill:#90EE90
    style S4 fill:#90EE90
    style S5 fill:#90EE90
    style S6 fill:#90EE90
    style S7 fill:#90EE90
    style W1 fill:#FFE4B5
    style W2 fill:#FFE4B5
    style W3 fill:#FFE4B5
    style W4 fill:#FFE4B5
    style W5 fill:#FFE4B5
    style D1 fill:#FFB6C1
    style D2 fill:#FFB6C1
    style D3 fill:#FFB6C1
```

---

## Vulnerability & Performance Analysis

### Security Findings

| # | Issue | Severity | Location | Status |
|---|-------|----------|----------|--------|
| 1 | **Hardcoded fallback secret key** | MEDIUM | app.py:20 | Set `SECRET_KEY` env var in Vercel |
| 2 | **Default user credentials** | LOW | database.py init | Only created on fresh DB (admin/admin123) |
| 3 | **SQL where_clause via f-string** | LOW* | app.py:1554,1572,1633,4098,4139 | Safe — clause is hardcoded strings with `?` params, but pattern is fragile |
| 4 | **File path traversal** | MITIGATED | Download bill routes | Flask's `send_file` + path construction limits risk |
| 5 | **No rate limiting on login** | MEDIUM | app.py:89 | Brute force possible |
| 6 | **No CSRF protection** | MEDIUM | All POST forms | Flask-WTF not used; session-based but no token validation |

*\*SQL injection classification: The `where_clause` is built from hardcoded column conditions (e.g., `"p.product_id = ?"`) with user values passed as params. Not directly exploitable but the f-string pattern is risky if future developers add unsanitized input.*

### Performance Findings

| # | Issue | Impact | Routes Affected |
|---|-------|--------|-----------------|
| 1 | **Cold start schema init over network** | **CRITICAL** — 5-8s of 10s budget | Every first request after Lambda recycle |
| 2 | **Unused reportlab import at module level** | ~0.1s wasted on every cold start | Every request (via reports.py import) |
| 3 | **N+1 query in warehouse_balance_all()** | O(n) DB calls where n = warehouse count | /warehouse/balance |
| 4 | **N+1 query in rake_summary_excel()** | O(n) DB calls where n = rake count | /admin/download-rake-summary-excel |
| 5 | **9 Excel download routes with heavy I/O** | 5-15s each (openpyxl + large queries) | /admin/download-*-excel |
| 6 | **Unused warehouse stock totals in dashboard query** | 2 extra full-table scans | /admin/dashboard |

### Fixes Applied

| # | Fix | Effect |
|---|-----|--------|
| 1 | **Skip `initialize_database()` for cloud** | **Saves 5-8s** on cold start — schema already exists in Turso |
| 2 | **Remove unused `from reports import ReportGenerator`** | **Saves ~0.1s** — no reportlab loaded at import time |
| 3 | **Remove `time.sleep(0.3)` in connection retry** | **Saves 0.3s** on connection failure path |
| 4 | **Remove total_stock_in/out from dashboard stats query** | **Saves ~0.2s** — 2 fewer full-table scans |
| 5 | **Add empty-state handling in day-wise stock template** | Shows "No data" instead of blank table on error |

### Remaining Recommendations (Not Yet Fixed)

1. **Excel downloads**: Move to client-side generation or async worker (these will always risk timeout)
2. **Warehouse balance N+1**: Refactor to single batch query with GROUP BY warehouse_id
3. **Add CSRF tokens**: Install Flask-WTF for form protection
4. **Add login rate limiting**: Use Flask-Limiter or custom middleware
5. **Set `SECRET_KEY`**: Ensure env var is configured in Vercel (never use fallback in prod)
6. **Connection pool tuning**: Reduce 300s TTL to 60s on Turso connection to handle stale Lambda connections faster

### Test Pipeline Results

- **83/83 tests passing**
- Test categories: Cache (5), Database (16), Auth (9), Authorization (5), Security (7), Performance (6), Route Integration (27), API (1), Timeout Risk (8)
