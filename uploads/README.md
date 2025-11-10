# Uploads Directory

This directory contains all uploaded files for the FIMS system.

## Structure

```
uploads/
├── eway_bills/          # Eway bill PDF files
│   └── [ebill_number]_[timestamp].pdf
└── README.md           # This file
```

## Eway Bills Storage

- **Location**: `uploads/eway_bills/`
- **Format**: PDF files only (max 5MB)
- **Naming Convention**: `{ebill_number}_{YYYYMMDD_HHMMSS}.pdf`
- **Example**: `EB001_20251020_143025.pdf`

## Access Control

- Only Accountant users can upload and download eway bill PDFs
- Files are served through Flask route: `/accountant/download-eway-bill/<filename>`
- Direct file access is blocked by server configuration

## Database Reference

- PDF filename is stored in `ebills.eway_bill_pdf` column
- Full path is constructed at runtime: `uploads/eway_bills/{filename}`

## Backup Recommendations

1. Regular backups of this directory should be made
2. Store backups in a secure, off-site location
3. Include this directory in disaster recovery plans

## Security Notes

- Ensure proper file permissions (read/write for application only)
- Validate file types on upload (PDF only)
- Scan files for malware before storage
- Never expose direct filesystem paths to users
