# AI Chatbot Customizations

This document tracks all customizations made to the Vercel AI Chatbot reference implementation.

## Overview
- **Base Repository**: https://github.com/vercel/ai-chatbot
- **Our Customized Version**: `ai-chatbot-reference/`
- **Clean Reference**: `vercel_ai_chatbot/` (git submodule)

## Key Customizations

### 1. Enhanced Guest User Experience
- **File**: `ai-chatbot-reference/lib/ai/entitlements.ts`
- **Change**: Increased guest user message limit from 1 to 3 messages per day
- **Reason**: Better user experience before requiring registration

### 2. Database Configuration
- **File**: `ai-chatbot-reference/.env.local`
- **Change**: Connected to dedicated `chatbot` database instead of default
- **Database**: `postgresql://temporal:temporal@localhost:5432/chatbot`
- **Reason**: Separation from Temporal workflow engine database

### 3. API Route Fixes
- **File**: `ai-chatbot-reference/app/(chat)/api/chat/route.simple.ts`
- **Change**: Fixed TypeScript errors by updating message structure
- **Details**: Replaced `text` field with `parts` and `attachments` arrays
- **Reason**: Compatibility with latest AI SDK

### 4. Registration Dialog Updates
- **File**: `ai-chatbot-reference/components/chat.tsx`
- **Change**: Updated messaging to reflect 3-message limit
- **Reason**: Consistency with entitlements changes

## File Structure Differences

### Added Files
- `app/(chat)/api/chat/route.simple.ts` - Simplified API route for testing

### Modified Files
- `lib/ai/entitlements.ts` - Guest user limits
- `components/chat.tsx` - Registration dialog
- `.env.local` - Database configuration

## Syncing Strategy

When updating from upstream Vercel AI Chatbot:

1. **Check for updates** in the clean reference:
   ```bash
   cd vercel_ai_chatbot
   git pull origin main
   ```

2. **Compare changes** between versions:
   ```bash
   diff -r vercel_ai_chatbot/ ai-chatbot-reference/ --exclude=node_modules --exclude=.git
   ```

3. **Selectively apply updates** while preserving customizations

4. **Test thoroughly** after any upstream merges

## Migration Notes

- Database tables created: User, Chat, Message_v2, Vote_v2, Document
- Environment variables configured for PostgreSQL connection
- All secret references use environment variables (no hardcoded values)

## Testing Checklist

- [ ] Guest user can send 3 messages before registration prompt
- [ ] Database connection works with chatbot database
- [ ] TypeScript compilation passes
- [ ] Chat functionality works end-to-end
- [ ] Registration flow works correctly

## Future Enhancements

- Integration with Temporal workflows for advanced chat features
- Custom AI models and providers
- Enhanced security and rate limiting
- Analytics and monitoring integration
