"""This file contains ONT barcode data as defined in LIMS, and patterns for parsing them."""

# Capture groups are: (1) barcode well, (2) barcode number, (3) barcode sequence
ONT_BARCODE_LABEL_PATTERN = r"\d{2}_([A-H][0-1]?\d)_NB(\d{2}) \(([ACGT]+)\)$"

# List of ONT barcodes, pulled from LIMS labels 'Nanopore native barcodes v2' 2024-04-02 by Alfred Kedhammar
ont_barcodes = [
    "01_A1_NB01 (CACAAAGACACCGACAACTTTCTT)",
    "02_B1_NB02 (ACAGACGACTACAAACGGAATCGA)",
    "03_C1_NB03 (CCTGGTAACTGGGACACAAGACTC)",
    "04_D1_NB04 (TAGGGAAACACGATAGAATCCGAA)",
    "05_E1_NB05 (AAGGTTACACAAACCCTGGACAAG)",
    "06_F1_NB06 (GACTACTTTCTGCCTTTGCGAGAA)",
    "07_G1_NB07 (AAGGATTCATTCCCACGGTAACAC)",
    "08_H1_NB08 (ACGTAACTTGGTTTGTTCCCTGAA)",
    "09_A2_NB09 (AACCAAGACTCGCTGTGCCTAGTT)",
    "10_B2_NB10 (GAGAGGACAAAGGTTTCAACGCTT)",
    "11_C2_NB11 (TCCATTCCCTCCGATAGATGAAAC)",
    "12_D2_NB12 (TCCGATTCTGCTTCTTTCTACCTG)",
    "13_E2_NB13 (AGAACGACTTCCATACTCGTGTGA)",
    "14_F2_NB14 (AACGAGTCTCTTGGGACCCATAGA)",
    "15_G2_NB15 (AGGTCTACCTCGCTAACACCACTG)",
    "16_H2_NB16 (CGTCAACTGACAGTGGTTCGTACT)",
    "17_A3_NB17 (ACCCTCCAGGAAAGTACCTCTGAT)",
    "18_B3_NB18 (CCAAACCCAACAACCTAGATAGGC)",
    "19_C3_NB19 (GTTCCTCGTGCAGTGTCAAGAGAT)",
    "20_D3_NB20 (TTGCGTCCTGTTACGAGAACTCAT)",
    "21_E3_NB21 (GAGCCTCTCATTGTCCGTTCTCTA)",
    "22_F3_NB22 (ACCACTGCCATGTATCAAAGTACG)",
    "23_G3_NB23 (CTTACTACCCAGTGAACCTCCTCG)",
    "24_H3_NB24 (GCATAGTTCTGCATGATGGGTTAG)",
    "25_A4_NB25 (GTAAGTTGGGTATGCAACGCAATG)",
    "26_B4_NB26 (CATACAGCGACTACGCATTCTCAT)",
    "27_C4_NB27 (CGACGGTTAGATTCACCTCTTACA)",
    "28_D4_NB28 (TGAAACCTAAGAAGGCACCGTATC)",
    "29_E4_NB29 (CTAGACACCTTGGGTTGACAGACC)",
    "30_F4_NB30 (TCAGTGAGGATCTACTTCGACCCA)",
    "31_G4_NB31 (TGCGTACAGCAATCAGTTACATTG)",
    "32_H4_NB32 (CCAGTAGAAGTCCGACAACGTCAT)",
    "33_A5_NB33 (CAGACTTGGTACGGTTGGGTAACT)",
    "34_B5_NB34 (GGACGAAGAACTCAAGTCAAAGGC)",
    "35_C5_NB35 (CTACTTACGAAGCTGAGGGACTGC)",
    "36_D5_NB36 (ATGTCCCAGTTAGAGGAGGAAACA)",
    "37_E5_NB37 (GCTTGCGATTGATGCTTAGTATCA)",
    "38_F5_NB38 (ACCACAGGAGGACGATACAGAGAA)",
    "39_G5_NB39 (CCACAGTGTCAACTAGAGCCTCTC)",
    "40_H5_NB40 (TAGTTTGGATGACCAAGGATAGCC)",
    "41_A6_NB41 (GGAGTTCGTCCAGAGAAGTACACG)",
    "42_B6_NB42 (CTACGTGTAAGGCATACCTGCCAG)",
    "43_C6_NB43 (CTTTCGTTGTTGACTCGACGGTAG)",
    "44_D6_NB44 (AGTAGAAAGGGTTCCTTCCCACTC)",
    "45_E6_NB45 (GATCCAACAGAGATGCCTTCAGTG)",
    "46_F6_NB46 (GCTGTGTTCCACTTCATTCTCCTG)",
    "47_G6_NB47 (GTGCAACTTTCCCACAGGTAGTTC)",
    "48_H6_NB48 (CATCTGGAACGTGGTACACCTGTA)",
    "49_A7_NB49 (ACTGGTGCAGCTTTGAACATCTAG)",
    "50_B7_NB50 (ATGGACTTTGGTAACTTCCTGCGT)",
    "51_C7_NB51 (GTTGAATGAGCCTACTGGGTCCTC)",
    "52_D7_NB52 (TGAGAGACAAGATTGTTCGTGGAC)",
    "53_E7_NB53 (AGATTCAGACCGTCTCATGCAAAG)",
    "54_F7_NB54 (CAAGAGCTTTGACTAAGGAGCATG)",
    "55_G7_NB55 (TGGAAGATGAGACCCTGATCTACG)",
    "56_H7_NB56 (TCACTACTCAACAGGTGGCATGAA)",
    "57_A8_NB57 (GCTAGGTCAATCTCCTTCGGAAGT)",
    "58_B8_NB58 (CAGGTTACTCCTCCGTGAGTCTGA)",
    "59_C8_NB59 (TCAATCAAGAAGGGAAAGCAAGGT)",
    "60_D8_NB60 (CATGTTCAACCAAGGCTTCTATGG)",
    "61_E8_NB61 (AGAGGGTACTATGTGCCTCAGCAC)",
    "62_F8_NB62 (CACCCACACTTACTTCAGGACGTA)",
    "63_G8_NB63 (TTCTGAAGTTCCTGGGTCTTGAAC)",
    "64_H8_NB64 (GACAGACACCGTTCATCGACTTTC)",
    "65_A9_NB65 (TTCTCAGTCTTCCTCCAGACAAGG)",
    "66_B9_NB66 (CCGATCCTTGTGGCTTCTAACTTC)",
    "67_C9_NB67 (GTTTGTCATACTCGTGTGCTCACC)",
    "68_D9_NB68 (GAATCTAAGCAAACACGAAGGTGG)",
    "69_E9_NB69 (TACAGTCCGAGCCTCATGTGATCT)",
    "70_F9_NB70 (ACCGAGATCCTACGAATGGAGTGT)",
    "71_G9_NB71 (CCTGGGAGCATCAGGTAGTAACAG)",
    "72_H9_NB72 (TAGCTGACTGTCTTCCATACCGAC)",
    "73_A10_NB73 (AAGAAACAGGATGACAGAACCCTC)",
    "74_B10_NB74 (TACAAGCATCCCAACACTTCCACT)",
    "75_C10_NB75 (GACCATTGTGATGAACCCTGTTGT)",
    "76_D10_NB76 (ATGCTTGTTACATCAACCCTGGAC)",
    "77_E10_NB77 (CGACCTGTTTCTCAGGGATACAAC)",
    "78_F10_NB78 (AACAACCGAACCTTTGAATCAGAA)",
    "79_G10_NB79 (TCTCGGAGATAGTTCTCACTGCTG)",
    "80_H10_NB80 (CGGATGAACATAGGATAGCGATTC)",
    "81_A11_NB81 (CCTCATCTTGTGAAGTTGTTTCGG)",
    "82_B11_NB82 (ACGGTATGTCGAGTTCCAGGACTA)",
    "83_C11_NB83 (TGGCTTGATCTAGGTAAGGTCGAA)",
    "84_D11_NB84 (GTAGTGGACCTAGAACCTGTGCCA)",
    "85_E11_NB85 (AACGGAGGAGTTAGTTGGATGATC)",
    "86_F11_NB86 (AGGTGATCCCAACAAGCGTAAGTA)",
    "87_G11_NB87 (TACATGCTCCTGTTGTTAGGGAGG)",
    "88_H11_NB88 (TCTTCTACTACCGATCCGAAGCAG)",
    "89_A12_NB89 (ACAGCATCAATGTTTGGCTAGTTG)",
    "90_B12_NB90 (GATGTAGAGGGTACGGTTTGAGGC)",
    "91_C12_NB91 (GGCTCCATAGGAACTCACGCTACT)",
    "92_D12_NB92 (TTGTGAGTGGAAAGATACAGGACC)",
    "93_E12_NB93 (AGTTTCCATCACTTCAGACTTGGG)",
    "94_F12_NB94 (GATTGTCCTCAAACTGCCACCTAC)",
    "95_G12_NB95 (CCTGTCTGGAAGAAGAATGGACTT)",
    "96_H12_NB96 (CTGAACGGTCATAGAGTCCACCAT)",
]

# Keyed by barcode number
ont_barcodes_num2label = {
    int(barcode[0:2].lstrip("0")): barcode for barcode in ont_barcodes
}

# Keyed by well name
ont_barcodes_well2label = {
    int(barcode.split("_")[1]): barcode for barcode in ont_barcodes
}
