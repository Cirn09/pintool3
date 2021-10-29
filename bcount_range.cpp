/*
 * Copyright 2002-2020 Intel Corporation.
 * 
 * This software is provided to you as Sample Source Code as defined in the accompanying
 * End User License Agreement for the Intel(R) Software Development Products ("Agreement")
 * section 1.L.
 * 
 * This software and the related documents are provided as is, with no express or implied
 * warranties, other than those that are expressly stated in the License.
 */

/*! @file
 *  This file contains a code coverage analyzer
 */

#include "pin.H"
#include <set>
#include <list>
#include <vector>
#include <iostream>
#include <fstream>
using std::cerr;
using std::dec;
using std::endl;
using std::hex;
using std::ios;
using std::list;
using std::set;
using std::string;
using std::vector;

#if defined(WIN32) || defined(_WIN32) || defined(WIN64) || defined(_WIN64)
#define PATH_SEP "\\"
#else
#define PATH_SEP "/"
#endif

bool iequals(const string &a, const string &b)
{
    size_t sz = a.size();
    if (b.size() != sz)
        return false;
    for (size_t i = 0; i < sz; ++i)
        if (tolower(a[i]) != tolower(b[i]))
            return false;
    return true;
}

/* ===================================================================== */
/* Commandline Switches */
/* ===================================================================== */

KNOB<string> KnobCountProcess(KNOB_MODE_WRITEONCE, "pintool", "p", "",
                              "Process name to count. (default: MainExecutable)");
KNOB<ADDRINT> KnobCountRangeStart(KNOB_MODE_WRITEONCE, "pintool", "s", "0",
                                  "Start *offset* of the record range. (default: 0)");
KNOB<ADDRINT> KnobCountRangeEnd(KNOB_MODE_WRITEONCE, "pintool", "e", "0",
                                "End *offset* of the record range. (default: end)");
KNOB<int> KnobCountType(KNOB_MODE_WRITEONCE, "pintool", "b", "0",
                        "Count on: 0. all branch \n\t1. taken branch \n\t2. not taken branch");
KNOB<bool> KnobDebugLog(KNOB_MODE_WRITEONCE, "pintool", "d", "0",
                        "Debug log. (default: false)");

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    cerr << "This pin tool count branch"
            "\n";

    cerr << KNOB_BASE::StringKnobSummary() << endl;
    return -1;
}

/* ===================================================================== */
/* Global Variables */
/* ===================================================================== */

UINT64 bcount = 0;
ADDRINT range_start = 0;
ADDRINT range_end = 0;

/* ===================================================================== */

VOID count_plus() { bcount++; }
VOID count_sub() { bcount--; }

/* ===================================================================== */
bool INS_IsConditionalBranch(INS ins)
{
    OPCODE opcode = INS_Opcode(ins);
    if (opcode == XED_ICLASS_JB ||
        opcode == XED_ICLASS_JBE ||
        opcode == XED_ICLASS_JCXZ ||
        opcode == XED_ICLASS_JECXZ ||
        opcode == XED_ICLASS_JL ||
        opcode == XED_ICLASS_JLE ||
        // opcode == XED_ICLASS_JMP ||
        // opcode == XED_ICLASS_JMP_FAR ||
        opcode == XED_ICLASS_JNB ||
        opcode == XED_ICLASS_JNBE ||
        opcode == XED_ICLASS_JNL ||
        opcode == XED_ICLASS_JNLE ||
        opcode == XED_ICLASS_JNO ||
        opcode == XED_ICLASS_JNP ||
        opcode == XED_ICLASS_JNS ||
        opcode == XED_ICLASS_JNZ ||
        opcode == XED_ICLASS_JO ||
        opcode == XED_ICLASS_JP ||
        opcode == XED_ICLASS_JRCXZ ||
        opcode == XED_ICLASS_JS ||
        opcode == XED_ICLASS_JZ)
        return true;
    return false;
}

VOID Instruction(INS ins, VOID *v)
{
    static int CountType = KnobCountType.Value();
    if (!range_end)
        return;
    // if (!INS_IsConditionalBranch(ins))
    if (!INS_IsDirectBranch(ins))
        return;

    ADDRINT addr = INS_Address(ins);
    if (range_start <= addr && addr <= range_end)
    {
        // if (range_start + 0xCC240 <= addr && addr <= range_start + 0x103DAB)
        if (CountType == 0)
        {
            // count on all branch
            INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR)count_plus, IARG_END);
        }
        else if (CountType == 1)
        {
            // count on taken branch
            INS_InsertCall(ins, IPOINT_TAKEN_BRANCH, (AFUNPTR)count_plus, IARG_END);
        }
        else if (CountType == 2)
        {
            // count on not taken branch
            INS_InsertCall(ins, IPOINT_BEFORE, (AFUNPTR)count_plus, IARG_END);
            INS_InsertCall(ins, IPOINT_TAKEN_BRANCH, (AFUNPTR)count_sub, IARG_END);
        }
    }
}

/* ===================================================================== */

VOID Fini(INT32 code, VOID *v) { cerr << "Count " << bcount << endl; }

/* ===================================================================== */

VOID Imageload(IMG img, VOID *v)
{
    if (range_start)
        return;

    string targetName = KnobCountProcess.Value();
    if (!targetName.empty())
    {
        const string imgName = IMG_Name(img);
        if (!iequals(targetName, imgName.substr(imgName.rfind(PATH_SEP) + 1)))
            return;
    }
    else if (!IMG_IsMainExecutable(img))
        return;

    ADDRINT img_start = IMG_StartAddress(img);
    if (!img_start)
        return;

    ADDRINT start_offset = KnobCountRangeStart.Value();
    // if (!start_offset)
    //     range_start = img_start;
    // else
    //     range_start = img_start + start_offset;
    range_start = img_start + start_offset;

    SEC sec_end = IMG_SecTail(img);
    ADDRINT img_end = SEC_Address(sec_end) + SEC_Size(sec_end);
    ADDRINT end_offset = KnobCountRangeEnd.Value();
    if (!end_offset)
        range_end = img_end;
    else
        range_end = img_start + end_offset;
    static bool debug = KnobDebugLog.Value();
    if (debug)
    {
        cerr << hex;
        cerr << "start: 0x" << range_start << endl;
        cerr << "end: 0x" << range_end << endl;
        cerr << dec;
    }
    return;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, CHAR *argv[])
{
    PIN_InitSymbols();

    if (PIN_Init(argc, argv))
    {
        return Usage();
    }

    PIN_AddFiniFunction(Fini, 0);

    INS_AddInstrumentFunction(Instruction, 0);
    IMG_AddInstrumentFunction(Imageload, 0);

    // Never returns

    PIN_StartProgram();

    return 0;
}

/* ===================================================================== */
/* eof */
/* ===================================================================== */
