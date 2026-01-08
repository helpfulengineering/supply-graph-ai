#!/bin/bash
# OME to OHM Renaming Verification Script
# 
# This script verifies that all OME references have been replaced with OHM.
# Run this script BEFORE and AFTER the renaming to ensure completeness.
#
# Usage:
#   ./scripts/verify_ome_to_ohm.sh [pre|post]
#
#   pre  - Run before renaming (baseline inventory)
#   post - Run after renaming (verification)
#
# If no argument is provided, assumes "post" (verification mode)

MODE=${1:-post}
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "=========================================="
echo "OME to OHM Renaming Verification"
echo "Mode: $MODE"
echo "Timestamp: $TIMESTAMP"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
OME_COUNT=0
OPEN_MATCHING_COUNT=0
OHM_COUNT=0
OPEN_HARDWARE_COUNT=0
ISSUES=0

echo "1. Checking for 'OME' word matches (case-sensitive)..."
OME_RESULTS=$(grep -r "\bOME\b" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.txt" --include="*.sh" --include="*.conf" 2>/dev/null | grep -v "prometheus" | grep -v "SOME" | grep -v "AWESOME" | wc -l | tr -d ' ')
OME_COUNT=$OME_RESULTS
if [ "$MODE" = "post" ] && [ "$OME_COUNT" -gt 0 ]; then
    echo -e "   ${RED}✗ Found $OME_COUNT OME references${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "   ${GREEN}✓ Found $OME_COUNT OME references${NC}"
fi

echo ""
echo "2. Checking for 'Open Matching Engine' references..."
OPEN_MATCHING_RESULTS=$(grep -ri "Open Matching Engine" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.txt" --include="*.sh" --include="*.conf" 2>/dev/null | wc -l | tr -d ' ')
OPEN_MATCHING_COUNT=$OPEN_MATCHING_RESULTS
if [ "$MODE" = "post" ] && [ "$OPEN_MATCHING_COUNT" -gt 0 ]; then
    echo -e "   ${RED}✗ Found $OPEN_MATCHING_COUNT 'Open Matching Engine' references${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "   ${GREEN}✓ Found $OPEN_MATCHING_COUNT 'Open Matching Engine' references${NC}"
fi

echo ""
echo "3. Checking for 'OHM' word matches (case-sensitive)..."
OHM_RESULTS=$(grep -r "\bOHM\b" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.txt" --include="*.sh" --include="*.conf" 2>/dev/null | wc -l | tr -d ' ')
OHM_COUNT=$OHM_RESULTS
if [ "$MODE" = "post" ] && [ "$OHM_COUNT" -eq 0 ]; then
    echo -e "   ${RED}✗ Found $OHM_COUNT OHM references (expected > 0)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "   ${GREEN}✓ Found $OHM_COUNT OHM references${NC}"
fi

echo ""
echo "4. Checking for 'Open Hardware Manager' references..."
OPEN_HARDWARE_RESULTS=$(grep -ri "Open Hardware Manager" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.txt" --include="*.sh" --include="*.conf" 2>/dev/null | wc -l | tr -d ' ')
OPEN_HARDWARE_COUNT=$OPEN_HARDWARE_RESULTS
if [ "$MODE" = "post" ] && [ "$OPEN_HARDWARE_COUNT" -eq 0 ]; then
    echo -e "   ${RED}✗ Found $OPEN_HARDWARE_COUNT 'Open Hardware Manager' references (expected > 0)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "   ${GREEN}✓ Found $OPEN_HARDWARE_COUNT 'Open Hardware Manager' references${NC}"
fi

echo ""
echo "5. Checking for specific patterns..."

echo "   5a. OMEError references..."
OMEError_COUNT=$(grep -r "OMEError" --include="*.py" --include="*.md" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODE" = "post" ] && [ "$OMEError_COUNT" -gt 0 ]; then
    echo -e "      ${RED}✗ Found $OMEError_COUNT OMEError references${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "      ${GREEN}✓ Found $OMEError_COUNT OMEError references${NC}"
fi

echo "   5b. OHMError references..."
OHMError_COUNT=$(grep -r "OHMError" --include="*.py" --include="*.md" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODE" = "post" ] && [ "$OHMError_COUNT" -eq 0 ]; then
    echo -e "      ${RED}✗ Found $OHMError_COUNT OHMError references (expected > 0)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "      ${GREEN}✓ Found $OHMError_COUNT OHMError references${NC}"
fi

echo "   5c. ome_version references..."
ome_version_COUNT=$(grep -r "ome_version" --include="*.py" --include="*.md" --include="*.json" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODE" = "post" ] && [ "$ome_version_COUNT" -gt 0 ]; then
    echo -e "      ${RED}✗ Found $ome_version_COUNT ome_version references${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "      ${GREEN}✓ Found $ome_version_COUNT ome_version references${NC}"
fi

echo "   5d. ohm_version references..."
ohm_version_COUNT=$(grep -r "ohm_version" --include="*.py" --include="*.md" --include="*.json" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODE" = "post" ] && [ "$ohm_version_COUNT" -eq 0 ]; then
    echo -e "      ${RED}✗ Found $ohm_version_COUNT ohm_version references (expected > 0)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "      ${GREEN}✓ Found $ohm_version_COUNT ohm_version references${NC}"
fi

echo "   5e. map_ome_error references..."
map_ome_error_COUNT=$(grep -r "map_ome_error" --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODE" = "post" ] && [ "$map_ome_error_COUNT" -gt 0 ]; then
    echo -e "      ${RED}✗ Found $map_ome_error_COUNT map_ome_error references${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "      ${GREEN}✓ Found $map_ome_error_COUNT map_ome_error references${NC}"
fi

echo "   5f. map_ohm_error references..."
map_ohm_error_COUNT=$(grep -r "map_ohm_error" --include="*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MODE" = "post" ] && [ "$map_ohm_error_COUNT" -eq 0 ]; then
    echo -e "      ${RED}✗ Found $map_ohm_error_COUNT map_ohm_error references (expected > 0)${NC}"
    ISSUES=$((ISSUES + 1))
else
    echo -e "      ${GREEN}✓ Found $map_ohm_error_COUNT map_ohm_error references${NC}"
fi

echo ""
echo "6. Checking for file renames..."
if [ -f "ome" ]; then
    if [ "$MODE" = "post" ]; then
        echo -e "   ${RED}✗ 'ome' file still exists (should be renamed to 'ohm')${NC}"
        ISSUES=$((ISSUES + 1))
    else
        echo -e "   ${GREEN}✓ 'ome' file exists (expected before renaming)${NC}"
    fi
else
    if [ "$MODE" = "post" ]; then
        echo -e "   ${GREEN}✓ 'ome' file does not exist (correctly renamed)${NC}"
    else
        echo -e "   ${YELLOW}⚠ 'ome' file not found (may have been renamed already)${NC}"
    fi
fi

if [ -f "ohm" ]; then
    if [ "$MODE" = "post" ]; then
        echo -e "   ${GREEN}✓ 'ohm' file exists (correctly renamed)${NC}"
    else
        echo -e "   ${YELLOW}⚠ 'ohm' file already exists${NC}"
    fi
else
    if [ "$MODE" = "post" ]; then
        echo -e "   ${RED}✗ 'ohm' file does not exist (should exist after renaming)${NC}"
        ISSUES=$((ISSUES + 1))
    else
        echo -e "   ${GREEN}✓ 'ohm' file does not exist (expected before renaming)${NC}"
    fi
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "OME references: $OME_COUNT"
echo "'Open Matching Engine' references: $OPEN_MATCHING_COUNT"
echo "OHM references: $OHM_COUNT"
echo "'Open Hardware Manager' references: $OPEN_HARDWARE_COUNT"
echo ""

if [ "$MODE" = "post" ]; then
    if [ "$ISSUES" -eq 0 ]; then
        echo -e "${GREEN}✓ Verification PASSED - No issues found${NC}"
        exit 0
    else
        echo -e "${RED}✗ Verification FAILED - Found $ISSUES issue(s)${NC}"
        echo ""
        echo "Please review the issues above and ensure all OME references have been replaced."
        exit 1
    fi
else
    echo -e "${GREEN}✓ Baseline inventory complete${NC}"
    echo ""
    echo "This is the baseline before renaming. After renaming, run this script"
    echo "again with 'post' mode to verify all changes were made correctly."
    exit 0
fi
