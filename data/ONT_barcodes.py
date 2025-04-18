import re

DESC = """This module contains ONT barcode data and builds some data structures to organize it.

# ONT documentation on barcoding kits
https://nanoporetech.com/document/chemistry-technical-document#barcoding-kits
https://nanoporetech.com/document/chemistry-technical-document#barcode-sequences

"""

# This dictionary unequivocally maps an ONT barcode name to a sequence
# Fetched and built 2025-03-19 by Alfred Kedhammar
# from https://nanoporetech.com/document/chemistry-technical-document#barcode-sequences
ont_name2seq: dict[str, str] = {
    "16S01": "AAGAAAGTTGTCGGTGTCTTTGTG",
    "16S02": "TCGATTCCGTTTGTAGTCGTCTGT",
    "16S03": "GAGTCTTGTGTCCCAGTTACCAGG",
    "16S04": "TTCGGATTCTATCGTGTTTCCCTA",
    "16S05": "CTTGTCCAGGGTTTGTGTAACCTT",
    "16S06": "TTCTCGCAAAGGCAGAAAGTAGTC",
    "16S07": "GTGTTACCGTGGGAATGAATCCTT",
    "16S08": "TTCAGGGAACAAACCAAGTTACGT",
    "16S09": "AACTAGGCACAGCGAGTCTTGGTT",
    "16S10": "AAGCGTTGAAACCTTTGTCCTCTC",
    "16S11": "GTTTCATCTATCGGAGGGAATGGA",
    "16S12": "CAGGTAGAAAGAAGCAGAATCGGA",
    "16S13": "AGAACGACTTCCATACTCGTGTGA",
    "16S14": "AACGAGTCTCTTGGGACCCATAGA",
    "16S15": "AGGTCTACCTCGCTAACACCACTG",
    "16S16": "CGTCAACTGACAGTGGTTCGTACT",
    "16S17": "ACCCTCCAGGAAAGTACCTCTGAT",
    "16S18": "CCAAACCCAACAACCTAGATAGGC",
    "16S19": "GTTCCTCGTGCAGTGTCAAGAGAT",
    "16S20": "TTGCGTCCTGTTACGAGAACTCAT",
    "16S21": "GAGCCTCTCATTGTCCGTTCTCTA",
    "16S22": "ACCACTGCCATGTATCAAAGTACG",
    "16S23": "CTTACTACCCAGTGAACCTCCTCG",
    "16S24": "GCATAGTTCTGCATGATGGGTTAG",
    "BC01": "AAGAAAGTTGTCGGTGTCTTTGTG",
    "BC02": "TCGATTCCGTTTGTAGTCGTCTGT",
    "BC03": "GAGTCTTGTGTCCCAGTTACCAGG",
    "BC04": "TTCGGATTCTATCGTGTTTCCCTA",
    "BC05": "CTTGTCCAGGGTTTGTGTAACCTT",
    "BC06": "TTCTCGCAAAGGCAGAAAGTAGTC",
    "BC07": "GTGTTACCGTGGGAATGAATCCTT",
    "BC08": "TTCAGGGAACAAACCAAGTTACGT",
    "BC09": "AACTAGGCACAGCGAGTCTTGGTT",
    "BC10": "AAGCGTTGAAACCTTTGTCCTCTC",
    "BC11": "GTTTCATCTATCGGAGGGAATGGA",
    "BC12": "CAGGTAGAAAGAAGCAGAATCGGA",
    "BC13": "AGAACGACTTCCATACTCGTGTGA",
    "BC14": "AACGAGTCTCTTGGGACCCATAGA",
    "BC15": "AGGTCTACCTCGCTAACACCACTG",
    "BC16": "CGTCAACTGACAGTGGTTCGTACT",
    "BC17": "ACCCTCCAGGAAAGTACCTCTGAT",
    "BC18": "CCAAACCCAACAACCTAGATAGGC",
    "BC19": "GTTCCTCGTGCAGTGTCAAGAGAT",
    "BC20": "TTGCGTCCTGTTACGAGAACTCAT",
    "BC21": "GAGCCTCTCATTGTCCGTTCTCTA",
    "BC22": "ACCACTGCCATGTATCAAAGTACG",
    "BC23": "CTTACTACCCAGTGAACCTCCTCG",
    "BC24": "GCATAGTTCTGCATGATGGGTTAG",
    "BC25": "GTAAGTTGGGTATGCAACGCAATG",
    "BC26": "CATACAGCGACTACGCATTCTCAT",
    "BC27": "CGACGGTTAGATTCACCTCTTACA",
    "BC28": "TGAAACCTAAGAAGGCACCGTATC",
    "BC29": "CTAGACACCTTGGGTTGACAGACC",
    "BC30": "TCAGTGAGGATCTACTTCGACCCA",
    "BC31": "TGCGTACAGCAATCAGTTACATTG",
    "BC32": "CCAGTAGAAGTCCGACAACGTCAT",
    "BC33": "CAGACTTGGTACGGTTGGGTAACT",
    "BC34": "GGACGAAGAACTCAAGTCAAAGGC",
    "BC35": "CTACTTACGAAGCTGAGGGACTGC",
    "BC36": "ATGTCCCAGTTAGAGGAGGAAACA",
    "BC37": "GCTTGCGATTGATGCTTAGTATCA",
    "BC38": "ACCACAGGAGGACGATACAGAGAA",
    "BC39": "CCACAGTGTCAACTAGAGCCTCTC",
    "BC40": "TAGTTTGGATGACCAAGGATAGCC",
    "BC41": "GGAGTTCGTCCAGAGAAGTACACG",
    "BC42": "CTACGTGTAAGGCATACCTGCCAG",
    "BC43": "CTTTCGTTGTTGACTCGACGGTAG",
    "BC44": "AGTAGAAAGGGTTCCTTCCCACTC",
    "BC45": "GATCCAACAGAGATGCCTTCAGTG",
    "BC46": "GCTGTGTTCCACTTCATTCTCCTG",
    "BC47": "GTGCAACTTTCCCACAGGTAGTTC",
    "BC48": "CATCTGGAACGTGGTACACCTGTA",
    "BC49": "ACTGGTGCAGCTTTGAACATCTAG",
    "BC50": "ATGGACTTTGGTAACTTCCTGCGT",
    "BC51": "GTTGAATGAGCCTACTGGGTCCTC",
    "BC52": "TGAGAGACAAGATTGTTCGTGGAC",
    "BC53": "AGATTCAGACCGTCTCATGCAAAG",
    "BC54": "CAAGAGCTTTGACTAAGGAGCATG",
    "BC55": "TGGAAGATGAGACCCTGATCTACG",
    "BC56": "TCACTACTCAACAGGTGGCATGAA",
    "BC57": "GCTAGGTCAATCTCCTTCGGAAGT",
    "BC58": "CAGGTTACTCCTCCGTGAGTCTGA",
    "BC59": "TCAATCAAGAAGGGAAAGCAAGGT",
    "BC60": "CATGTTCAACCAAGGCTTCTATGG",
    "BC61": "AGAGGGTACTATGTGCCTCAGCAC",
    "BC62": "CACCCACACTTACTTCAGGACGTA",
    "BC63": "TTCTGAAGTTCCTGGGTCTTGAAC",
    "BC64": "GACAGACACCGTTCATCGACTTTC",
    "BC65": "TTCTCAGTCTTCCTCCAGACAAGG",
    "BC66": "CCGATCCTTGTGGCTTCTAACTTC",
    "BC67": "GTTTGTCATACTCGTGTGCTCACC",
    "BC68": "GAATCTAAGCAAACACGAAGGTGG",
    "BC69": "TACAGTCCGAGCCTCATGTGATCT",
    "BC70": "ACCGAGATCCTACGAATGGAGTGT",
    "BC71": "CCTGGGAGCATCAGGTAGTAACAG",
    "BC72": "TAGCTGACTGTCTTCCATACCGAC",
    "BC73": "AAGAAACAGGATGACAGAACCCTC",
    "BC74": "TACAAGCATCCCAACACTTCCACT",
    "BC75": "GACCATTGTGATGAACCCTGTTGT",
    "BC76": "ATGCTTGTTACATCAACCCTGGAC",
    "BC77": "CGACCTGTTTCTCAGGGATACAAC",
    "BC78": "AACAACCGAACCTTTGAATCAGAA",
    "BC79": "TCTCGGAGATAGTTCTCACTGCTG",
    "BC80": "CGGATGAACATAGGATAGCGATTC",
    "BC81": "CCTCATCTTGTGAAGTTGTTTCGG",
    "BC82": "ACGGTATGTCGAGTTCCAGGACTA",
    "BC83": "TGGCTTGATCTAGGTAAGGTCGAA",
    "BC84": "GTAGTGGACCTAGAACCTGTGCCA",
    "BC85": "AACGGAGGAGTTAGTTGGATGATC",
    "BC86": "AGGTGATCCCAACAAGCGTAAGTA",
    "BC87": "TACATGCTCCTGTTGTTAGGGAGG",
    "BC88": "TCTTCTACTACCGATCCGAAGCAG",
    "BC89": "ACAGCATCAATGTTTGGCTAGTTG",
    "BC90": "GATGTAGAGGGTACGGTTTGAGGC",
    "BC91": "GGCTCCATAGGAACTCACGCTACT",
    "BC92": "TTGTGAGTGGAAAGATACAGGACC",
    "BC93": "AGTTTCCATCACTTCAGACTTGGG",
    "BC94": "GATTGTCCTCAAACTGCCACCTAC",
    "BC95": "CCTGTCTGGAAGAAGAATGGACTT",
    "BC96": "CTGAACGGTCATAGAGTCCACCAT",
    "BP01": "AAGAAAGTTGTCGGTGTCTTTGTG",
    "BP02": "TCGATTCCGTTTGTAGTCGTCTGT",
    "BP03": "GAGTCTTGTGTCCCAGTTACCAGG",
    "BP04": "TTCGGATTCTATCGTGTTTCCCTA",
    "BP05": "CTTGTCCAGGGTTTGTGTAACCTT",
    "BP06": "TTCTCGCAAAGGCAGAAAGTAGTC",
    "BP07": "GTGTTACCGTGGGAATGAATCCTT",
    "BP08": "TTCAGGGAACAAACCAAGTTACGT",
    "BP09": "AACTAGGCACAGCGAGTCTTGGTT",
    "BP10": "AAGCGTTGAAACCTTTGTCCTCTC",
    "BP11": "GTTTCATCTATCGGAGGGAATGGA",
    "BP12": "CAGGTAGAAAGAAGCAGAATCGGA",
    "BP13": "AGAACGACTTCCATACTCGTGTGA",
    "BP14": "AACGAGTCTCTTGGGACCCATAGA",
    "BP15": "AGGTCTACCTCGCTAACACCACTG",
    "BP16": "CGTCAACTGACAGTGGTTCGTACT",
    "BP17": "ACCCTCCAGGAAAGTACCTCTGAT",
    "BP18": "CCAAACCCAACAACCTAGATAGGC",
    "BP19": "GTTCCTCGTGCAGTGTCAAGAGAT",
    "BP20": "TTGCGTCCTGTTACGAGAACTCAT",
    "BP21": "GAGCCTCTCATTGTCCGTTCTCTA",
    "BP22": "ACCACTGCCATGTATCAAAGTACG",
    "BP23": "CTTACTACCCAGTGAACCTCCTCG",
    "BP24": "GCATAGTTCTGCATGATGGGTTAG",
    "NB01": "CACAAAGACACCGACAACTTTCTT",
    "NB02": "ACAGACGACTACAAACGGAATCGA",
    "NB03": "CCTGGTAACTGGGACACAAGACTC",
    "NB04": "TAGGGAAACACGATAGAATCCGAA",
    "NB05": "AAGGTTACACAAACCCTGGACAAG",
    "NB06": "GACTACTTTCTGCCTTTGCGAGAA",
    "NB07": "AAGGATTCATTCCCACGGTAACAC",
    "NB08": "ACGTAACTTGGTTTGTTCCCTGAA",
    "NB09": "AACCAAGACTCGCTGTGCCTAGTT",
    "NB10": "GAGAGGACAAAGGTTTCAACGCTT",
    "NB11": "TCCATTCCCTCCGATAGATGAAAC",
    "NB12": "TCCGATTCTGCTTCTTTCTACCTG",
    "NB13": "AGAACGACTTCCATACTCGTGTGA",
    "NB14": "AACGAGTCTCTTGGGACCCATAGA",
    "NB15": "AGGTCTACCTCGCTAACACCACTG",
    "NB16": "CGTCAACTGACAGTGGTTCGTACT",
    "NB17": "ACCCTCCAGGAAAGTACCTCTGAT",
    "NB18": "CCAAACCCAACAACCTAGATAGGC",
    "NB19": "GTTCCTCGTGCAGTGTCAAGAGAT",
    "NB20": "TTGCGTCCTGTTACGAGAACTCAT",
    "NB21": "GAGCCTCTCATTGTCCGTTCTCTA",
    "NB22": "ACCACTGCCATGTATCAAAGTACG",
    "NB23": "CTTACTACCCAGTGAACCTCCTCG",
    "NB24": "GCATAGTTCTGCATGATGGGTTAG",
    "NB25": "GTAAGTTGGGTATGCAACGCAATG",
    "NB26": "CATACAGCGACTACGCATTCTCAT",
    "NB27": "CGACGGTTAGATTCACCTCTTACA",
    "NB28": "TGAAACCTAAGAAGGCACCGTATC",
    "NB29": "CTAGACACCTTGGGTTGACAGACC",
    "NB30": "TCAGTGAGGATCTACTTCGACCCA",
    "NB31": "TGCGTACAGCAATCAGTTACATTG",
    "NB32": "CCAGTAGAAGTCCGACAACGTCAT",
    "NB33": "CAGACTTGGTACGGTTGGGTAACT",
    "NB34": "GGACGAAGAACTCAAGTCAAAGGC",
    "NB35": "CTACTTACGAAGCTGAGGGACTGC",
    "NB36": "ATGTCCCAGTTAGAGGAGGAAACA",
    "NB37": "GCTTGCGATTGATGCTTAGTATCA",
    "NB38": "ACCACAGGAGGACGATACAGAGAA",
    "NB39": "CCACAGTGTCAACTAGAGCCTCTC",
    "NB40": "TAGTTTGGATGACCAAGGATAGCC",
    "NB41": "GGAGTTCGTCCAGAGAAGTACACG",
    "NB42": "CTACGTGTAAGGCATACCTGCCAG",
    "NB43": "CTTTCGTTGTTGACTCGACGGTAG",
    "NB44": "AGTAGAAAGGGTTCCTTCCCACTC",
    "NB45": "GATCCAACAGAGATGCCTTCAGTG",
    "NB46": "GCTGTGTTCCACTTCATTCTCCTG",
    "NB47": "GTGCAACTTTCCCACAGGTAGTTC",
    "NB48": "CATCTGGAACGTGGTACACCTGTA",
    "NB49": "ACTGGTGCAGCTTTGAACATCTAG",
    "NB50": "ATGGACTTTGGTAACTTCCTGCGT",
    "NB51": "GTTGAATGAGCCTACTGGGTCCTC",
    "NB52": "TGAGAGACAAGATTGTTCGTGGAC",
    "NB53": "AGATTCAGACCGTCTCATGCAAAG",
    "NB54": "CAAGAGCTTTGACTAAGGAGCATG",
    "NB55": "TGGAAGATGAGACCCTGATCTACG",
    "NB56": "TCACTACTCAACAGGTGGCATGAA",
    "NB57": "GCTAGGTCAATCTCCTTCGGAAGT",
    "NB58": "CAGGTTACTCCTCCGTGAGTCTGA",
    "NB59": "TCAATCAAGAAGGGAAAGCAAGGT",
    "NB60": "CATGTTCAACCAAGGCTTCTATGG",
    "NB61": "AGAGGGTACTATGTGCCTCAGCAC",
    "NB62": "CACCCACACTTACTTCAGGACGTA",
    "NB63": "TTCTGAAGTTCCTGGGTCTTGAAC",
    "NB64": "GACAGACACCGTTCATCGACTTTC",
    "NB65": "TTCTCAGTCTTCCTCCAGACAAGG",
    "NB66": "CCGATCCTTGTGGCTTCTAACTTC",
    "NB67": "GTTTGTCATACTCGTGTGCTCACC",
    "NB68": "GAATCTAAGCAAACACGAAGGTGG",
    "NB69": "TACAGTCCGAGCCTCATGTGATCT",
    "NB70": "ACCGAGATCCTACGAATGGAGTGT",
    "NB71": "CCTGGGAGCATCAGGTAGTAACAG",
    "NB72": "TAGCTGACTGTCTTCCATACCGAC",
    "NB73": "AAGAAACAGGATGACAGAACCCTC",
    "NB74": "TACAAGCATCCCAACACTTCCACT",
    "NB75": "GACCATTGTGATGAACCCTGTTGT",
    "NB76": "ATGCTTGTTACATCAACCCTGGAC",
    "NB77": "CGACCTGTTTCTCAGGGATACAAC",
    "NB78": "AACAACCGAACCTTTGAATCAGAA",
    "NB79": "TCTCGGAGATAGTTCTCACTGCTG",
    "NB80": "CGGATGAACATAGGATAGCGATTC",
    "NB81": "CCTCATCTTGTGAAGTTGTTTCGG",
    "NB82": "ACGGTATGTCGAGTTCCAGGACTA",
    "NB83": "TGGCTTGATCTAGGTAAGGTCGAA",
    "NB84": "GTAGTGGACCTAGAACCTGTGCCA",
    "NB85": "AACGGAGGAGTTAGTTGGATGATC",
    "NB86": "AGGTGATCCCAACAAGCGTAAGTA",
    "NB87": "TACATGCTCCTGTTGTTAGGGAGG",
    "NB88": "TCTTCTACTACCGATCCGAAGCAG",
    "NB89": "ACAGCATCAATGTTTGGCTAGTTG",
    "NB90": "GATGTAGAGGGTACGGTTTGAGGC",
    "NB91": "GGCTCCATAGGAACTCACGCTACT",
    "NB92": "TTGTGAGTGGAAAGATACAGGACC",
    "NB93": "AGTTTCCATCACTTCAGACTTGGG",
    "NB94": "GATTGTCCTCAAACTGCCACCTAC",
    "NB95": "CCTGTCTGGAAGAAGAATGGACTT",
    "NB96": "CTGAACGGTCATAGAGTCCACCAT",
    "RB01": "AAGAAAGTTGTCGGTGTCTTTGTG",
    "RB02": "TCGATTCCGTTTGTAGTCGTCTGT",
    "RB03": "GAGTCTTGTGTCCCAGTTACCAGG",
    "RB04": "TTCGGATTCTATCGTGTTTCCCTA",
    "RB05": "CTTGTCCAGGGTTTGTGTAACCTT",
    "RB06": "TTCTCGCAAAGGCAGAAAGTAGTC",
    "RB07": "GTGTTACCGTGGGAATGAATCCTT",
    "RB08": "TTCAGGGAACAAACCAAGTTACGT",
    "RB09": "AACTAGGCACAGCGAGTCTTGGTT",
    "RB10": "AAGCGTTGAAACCTTTGTCCTCTC",
    "RB11": "GTTTCATCTATCGGAGGGAATGGA",
    "RB12": "CAGGTAGAAAGAAGCAGAATCGGA",
    "RB13": "AGAACGACTTCCATACTCGTGTGA",
    "RB14": "AACGAGTCTCTTGGGACCCATAGA",
    "RB15": "AGGTCTACCTCGCTAACACCACTG",
    "RB16": "CGTCAACTGACAGTGGTTCGTACT",
    "RB17": "ACCCTCCAGGAAAGTACCTCTGAT",
    "RB18": "CCAAACCCAACAACCTAGATAGGC",
    "RB19": "GTTCCTCGTGCAGTGTCAAGAGAT",
    "RB20": "TTGCGTCCTGTTACGAGAACTCAT",
    "RB21": "GAGCCTCTCATTGTCCGTTCTCTA",
    "RB22": "ACCACTGCCATGTATCAAAGTACG",
    "RB23": "CTTACTACCCAGTGAACCTCCTCG",
    "RB24": "GCATAGTTCTGCATGATGGGTTAG",
    "RB25": "GTAAGTTGGGTATGCAACGCAATG",
    "RB26": "CATACAGCGACTACGCATTCTCAT",
    "RB27": "CGACGGTTAGATTCACCTCTTACA",
    "RB28": "TGAAACCTAAGAAGGCACCGTATC",
    "RB29": "CTAGACACCTTGGGTTGACAGACC",
    "RB30": "TCAGTGAGGATCTACTTCGACCCA",
    "RB31": "TGCGTACAGCAATCAGTTACATTG",
    "RB32": "CCAGTAGAAGTCCGACAACGTCAT",
    "RB33": "CAGACTTGGTACGGTTGGGTAACT",
    "RB34": "GGACGAAGAACTCAAGTCAAAGGC",
    "RB35": "CTACTTACGAAGCTGAGGGACTGC",
    "RB36": "ATGTCCCAGTTAGAGGAGGAAACA",
    "RB37": "GCTTGCGATTGATGCTTAGTATCA",
    "RB38": "ACCACAGGAGGACGATACAGAGAA",
    "RB39": "CCACAGTGTCAACTAGAGCCTCTC",
    "RB40": "TAGTTTGGATGACCAAGGATAGCC",
    "RB41": "GGAGTTCGTCCAGAGAAGTACACG",
    "RB42": "CTACGTGTAAGGCATACCTGCCAG",
    "RB43": "CTTTCGTTGTTGACTCGACGGTAG",
    "RB44": "AGTAGAAAGGGTTCCTTCCCACTC",
    "RB45": "GATCCAACAGAGATGCCTTCAGTG",
    "RB46": "GCTGTGTTCCACTTCATTCTCCTG",
    "RB47": "GTGCAACTTTCCCACAGGTAGTTC",
    "RB48": "CATCTGGAACGTGGTACACCTGTA",
    "RB49": "ACTGGTGCAGCTTTGAACATCTAG",
    "RB50": "ATGGACTTTGGTAACTTCCTGCGT",
    "RB51": "GTTGAATGAGCCTACTGGGTCCTC",
    "RB52": "TGAGAGACAAGATTGTTCGTGGAC",
    "RB53": "AGATTCAGACCGTCTCATGCAAAG",
    "RB54": "CAAGAGCTTTGACTAAGGAGCATG",
    "RB55": "TGGAAGATGAGACCCTGATCTACG",
    "RB56": "TCACTACTCAACAGGTGGCATGAA",
    "RB57": "GCTAGGTCAATCTCCTTCGGAAGT",
    "RB58": "CAGGTTACTCCTCCGTGAGTCTGA",
    "RB59": "TCAATCAAGAAGGGAAAGCAAGGT",
    "RB60": "CATGTTCAACCAAGGCTTCTATGG",
    "RB61": "AGAGGGTACTATGTGCCTCAGCAC",
    "RB62": "CACCCACACTTACTTCAGGACGTA",
    "RB63": "TTCTGAAGTTCCTGGGTCTTGAAC",
    "RB64": "GACAGACACCGTTCATCGACTTTC",
    "RB65": "TTCTCAGTCTTCCTCCAGACAAGG",
    "RB66": "CCGATCCTTGTGGCTTCTAACTTC",
    "RB67": "GTTTGTCATACTCGTGTGCTCACC",
    "RB68": "GAATCTAAGCAAACACGAAGGTGG",
    "RB69": "TACAGTCCGAGCCTCATGTGATCT",
    "RB70": "ACCGAGATCCTACGAATGGAGTGT",
    "RB71": "CCTGGGAGCATCAGGTAGTAACAG",
    "RB72": "TAGCTGACTGTCTTCCATACCGAC",
    "RB73": "AAGAAACAGGATGACAGAACCCTC",
    "RB74": "TACAAGCATCCCAACACTTCCACT",
    "RB75": "GACCATTGTGATGAACCCTGTTGT",
    "RB76": "ATGCTTGTTACATCAACCCTGGAC",
    "RB77": "CGACCTGTTTCTCAGGGATACAAC",
    "RB78": "AACAACCGAACCTTTGAATCAGAA",
    "RB79": "TCTCGGAGATAGTTCTCACTGCTG",
    "RB80": "CGGATGAACATAGGATAGCGATTC",
    "RB81": "CCTCATCTTGTGAAGTTGTTTCGG",
    "RB82": "ACGGTATGTCGAGTTCCAGGACTA",
    "RB83": "TGGCTTGATCTAGGTAAGGTCGAA",
    "RB84": "GTAGTGGACCTAGAACCTGTGCCA",
    "RB85": "AACGGAGGAGTTAGTTGGATGATC",
    "RB86": "AGGTGATCCCAACAAGCGTAAGTA",
    "RB87": "TACATGCTCCTGTTGTTAGGGAGG",
    "RB88": "TCTTCTACTACCGATCCGAAGCAG",
    "RB89": "ACAGCATCAATGTTTGGCTAGTTG",
    "RB90": "GATGTAGAGGGTACGGTTTGAGGC",
    "RB91": "GGCTCCATAGGAACTCACGCTACT",
    "RB92": "TTGTGAGTGGAAAGATACAGGACC",
    "RB93": "AGTTTCCATCACTTCAGACTTGGG",
    "RB94": "GATTGTCCTCAAACTGCCACCTAC",
    "RB95": "CCTGTCTGGAAGAAGAATGGACTT",
    "RB96": "CTGAACGGTCATAGAGTCCACCAT",
    "RLB01": "AAGAAAGTTGTCGGTGTCTTTGTG",
    "RLB012A": "GTTGAGTTACAAAGCACCGATCAG",
    "RLB02": "TCGATTCCGTTTGTAGTCGTCTGT",
    "RLB03": "GAGTCTTGTGTCCCAGTTACCAGG",
    "RLB04": "TTCGGATTCTATCGTGTTTCCCTA",
    "RLB05": "CTTGTCCAGGGTTTGTGTAACCTT",
    "RLB06": "TTCTCGCAAAGGCAGAAAGTAGTC",
    "RLB07": "GTGTTACCGTGGGAATGAATCCTT",
    "RLB08": "TTCAGGGAACAAACCAAGTTACGT",
    "RLB09": "AACTAGGCACAGCGAGTCTTGGTT",
    "RLB10": "AAGCGTTGAAACCTTTGTCCTCTC",
    "RLB11": "GTTTCATCTATCGGAGGGAATGGA",
    "RLB12": "GTTGAGTTACAAAGCACCGATCAG",
    "RLB13": "AGAACGACTTCCATACTCGTGTGA",
    "RLB14": "AACGAGTCTCTTGGGACCCATAGA",
    "RLB15": "AGGTCTACCTCGCTAACACCACTG",
    "RLB16": "CGTCAACTGACAGTGGTTCGTACT",
    "RLB17": "ACCCTCCAGGAAAGTACCTCTGAT",
    "RLB18": "CCAAACCCAACAACCTAGATAGGC",
    "RLB19": "GTTCCTCGTGCAGTGTCAAGAGAT",
    "RLB20": "TTGCGTCCTGTTACGAGAACTCAT",
    "RLB21": "GAGCCTCTCATTGTCCGTTCTCTA",
    "RLB22": "ACCACTGCCATGTATCAAAGTACG",
    "RLB23": "CTTACTACCCAGTGAACCTCCTCG",
    "RLB24": "GCATAGTTCTGCATGATGGGTTAG",
}

# This version of the dict allows a single sequence to map to multiple names
ont_seq2names: dict[str, list[str]] = {}
for name, seq in ont_name2seq.items():
    if seq not in ont_seq2names:
        ont_seq2names[seq] = [name]
    else:
        ont_seq2names[seq].append(name)

# This version of the dict groups the barcodes names by shared prefix
ont_grouped_name2seq: dict[str, dict[str, str]] = {}
for name, seq in ont_name2seq.items():
    # The shared name is whatever precedes the last group of digits in the name
    shared_prefix_match = re.match(r"^(.*?)(\d+[^0-9]*)$", name)
    assert shared_prefix_match is not None, f"Could not match shared prefix in {name}"
    shared_prefix = shared_prefix_match.group(1)
    if shared_prefix not in ont_grouped_name2seq:
        ont_grouped_name2seq[shared_prefix] = {}
    ont_grouped_name2seq[shared_prefix][name] = seq


# This dictionary contains the reagent label sets defined in LIMS
# Fetched from LIMS 2025-03-19 by Alfred Kedhammar
lims_kits2labels: dict[str, list[str]] = {
    "Nanopore native barcodes v2": [
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
    ],
    "EXP-PBC096": [
        "A01_BC01 (AAGAAAGTTGTCGGTGTCTTTGTG)",
        "A02_BC02 (TCGATTCCGTTTGTAGTCGTCTGT)",
        "A03_BC03 (GAGTCTTGTGTCCCAGTTACCAGG)",
        "A04_BC04 (TTCGGATTCTATCGTGTTTCCCTA)",
        "A05_BC05 (CTTGTCCAGGGTTTGTGTAACCTT)",
        "A06_BC06 (TTCTCGCAAAGGCAGAAAGTAGTC)",
        "A07_BC07 (GTGTTACCGTGGGAATGAATCCTT)",
        "A08_BC08 (TTCAGGGAACAAACCAAGTTACGT)",
        "A09_BC09 (AACTAGGCACAGCGAGTCTTGGTT)",
        "A10_BC10 (AAGCGTTGAAACCTTTGTCCTCTC)",
        "A11_BC11 (GTTTCATCTATCGGAGGGAATGGA)",
        "A12_BC12 (CAGGTAGAAAGAAGCAGAATCGGA)",
        "B01_BC13 (AGAACGACTTCCATACTCGTGTGA)",
        "B02_BC14 (AACGAGTCTCTTGGGACCCATAGA)",
        "B03_BC15 (AGGTCTACCTCGCTAACACCACTG)",
        "B04_BC16 (CGTCAACTGACAGTGGTTCGTACT)",
        "B05_BC17 (ACCCTCCAGGAAAGTACCTCTGAT)",
        "B06_BC18 (CCAAACCCAACAACCTAGATAGGC)",
        "B07_BC19 (GTTCCTCGTGCAGTGTCAAGAGAT)",
        "B08_BC20 (TTGCGTCCTGTTACGAGAACTCAT)",
        "B09_BC21 (GAGCCTCTCATTGTCCGTTCTCTA)",
        "B10_BC22 (ACCACTGCCATGTATCAAAGTACG)",
        "B11_BC23 (CTTACTACCCAGTGAACCTCCTCG)",
        "B12_BC24 (GCATAGTTCTGCATGATGGGTTAG)",
        "C01_BC25 (GTAAGTTGGGTATGCAACGCAATG)",
        "C02_BC26 (CATACAGCGACTACGCATTCTCAT)",
        "C03_BC27 (CGACGGTTAGATTCACCTCTTACA)",
        "C04_BC28 (TGAAACCTAAGAAGGCACCGTATC)",
        "C05_BC29 (CTAGACACCTTGGGTTGACAGACC)",
        "C06_BC30 (TCAGTGAGGATCTACTTCGACCCA)",
        "C07_BC31 (TGCGTACAGCAATCAGTTACATTG)",
        "C08_BC32 (CCAGTAGAAGTCCGACAACGTCAT)",
        "C09_BC33 (CAGACTTGGTACGGTTGGGTAACT)",
        "C10_BC34 (GGACGAAGAACTCAAGTCAAAGGC)",
        "C11_BC35 (CTACTTACGAAGCTGAGGGACTGC)",
        "C12_BC36 (ATGTCCCAGTTAGAGGAGGAAACA)",
        "D01_BC37 (GCTTGCGATTGATGCTTAGTATCA)",
        "D02_BC38 (ACCACAGGAGGACGATACAGAGAA)",
        "D03_BC39 (CCACAGTGTCAACTAGAGCCTCTC)",
        "D04_BC40 (TAGTTTGGATGACCAAGGATAGCC)",
        "D05_BC41 (GGAGTTCGTCCAGAGAAGTACACG)",
        "D06_BC42 (CTACGTGTAAGGCATACCTGCCAG)",
        "D07_BC43 (CTTTCGTTGTTGACTCGACGGTAG)",
        "D08_BC44 (AGTAGAAAGGGTTCCTTCCCACTC)",
        "D09_BC45 (GATCCAACAGAGATGCCTTCAGTG)",
        "D10_BC46 (GCTGTGTTCCACTTCATTCTCCTG)",
        "D11_BC47 (GTGCAACTTTCCCACAGGTAGTTC)",
        "D12_BC48 (CATCTGGAACGTGGTACACCTGTA)",
        "E01_BC49 (ACTGGTGCAGCTTTGAACATCTAG)",
        "E02_BC50 (ATGGACTTTGGTAACTTCCTGCGT)",
        "E03_BC51 (GTTGAATGAGCCTACTGGGTCCTC)",
        "E04_BC52 (TGAGAGACAAGATTGTTCGTGGAC)",
        "E05_BC53 (AGATTCAGACCGTCTCATGCAAAG)",
        "E06_BC54 (CAAGAGCTTTGACTAAGGAGCATG)",
        "E07_BC55 (TGGAAGATGAGACCCTGATCTACG)",
        "E08_BC56 (TCACTACTCAACAGGTGGCATGAA)",
        "E09_BC57 (GCTAGGTCAATCTCCTTCGGAAGT)",
        "E10_BC58 (CAGGTTACTCCTCCGTGAGTCTGA)",
        "E11_BC59 (TCAATCAAGAAGGGAAAGCAAGGT)",
        "E12_BC60 (CATGTTCAACCAAGGCTTCTATGG)",
        "F01_BC61 (AGAGGGTACTATGTGCCTCAGCAC)",
        "F02_BC62 (CACCCACACTTACTTCAGGACGTA)",
        "F03_BC63 (TTCTGAAGTTCCTGGGTCTTGAAC)",
        "F04_BC64 (GACAGACACCGTTCATCGACTTTC)",
        "F05_BC65 (TTCTCAGTCTTCCTCCAGACAAGG)",
        "F06_BC66 (CCGATCCTTGTGGCTTCTAACTTC)",
        "F07_BC67 (GTTTGTCATACTCGTGTGCTCACC)",
        "F08_BC68 (GAATCTAAGCAAACACGAAGGTGG)",
        "F09_BC69 (TACAGTCCGAGCCTCATGTGATCT)",
        "F10_BC70 (ACCGAGATCCTACGAATGGAGTGT)",
        "F11_BC71 (CCTGGGAGCATCAGGTAGTAACAG)",
        "F12_BC72 (TAGCTGACTGTCTTCCATACCGAC)",
        "G01_BC73 (AAGAAACAGGATGACAGAACCCTC)",
        "G02_BC74 (TACAAGCATCCCAACACTTCCACT)",
        "G03_BC75 (GACCATTGTGATGAACCCTGTTGT)",
        "G04_BC76 (ATGCTTGTTACATCAACCCTGGAC)",
        "G05_BC77 (CGACCTGTTTCTCAGGGATACAAC)",
        "G06_BC78 (AACAACCGAACCTTTGAATCAGAA)",
        "G07_BC79 (TCTCGGAGATAGTTCTCACTGCTG)",
        "G08_BC80 (CGGATGAACATAGGATAGCGATTC)",
        "G09_BC81 (CCTCATCTTGTGAAGTTGTTTCGG)",
        "G10_BC82 (ACGGTATGTCGAGTTCCAGGACTA)",
        "G11_BC83 (TGGCTTGATCTAGGTAAGGTCGAA)",
        "G12_BC84 (GTAGTGGACCTAGAACCTGTGCCA)",
        "H01_BC85 (AACGGAGGAGTTAGTTGGATGATC)",
        "H02_BC86 (AGGTGATCCCAACAAGCGTAAGTA)",
        "H03_BC87 (TACATGCTCCTGTTGTTAGGGAGG)",
        "H04_BC88 (TCTTCTACTACCGATCCGAAGCAG)",
        "H05_BC89 (ACAGCATCAATGTTTGGCTAGTTG)",
        "H06_BC90 (GATGTAGAGGGTACGGTTTGAGGC)",
        "H07_BC91 (GGCTCCATAGGAACTCACGCTACT)",
        "H08_BC92 (TTGTGAGTGGAAAGATACAGGACC)",
        "H09_BC93 (AGTTTCCATCACTTCAGACTTGGG)",
        "H10_BC94 (GATTGTCCTCAAACTGCCACCTAC)",
        "H11_BC95 (CCTGTCTGGAAGAAGAATGGACTT)",
        "H12_BC96 (CTGAACGGTCATAGAGTCCACCAT)",
    ],
}


def format_well(well: str) -> str:
    """Clean up a string specifying a plate well to fit standardized format.

    E.g.
    A:01 -> A:1
    G12 -> G:12
    b4 -> B:4

    """
    letter = well[0].upper()
    assert letter in "ABCDEFGH", f"Invalid row letter: {letter}"
    num = well[1:].lstrip("0").replace(":", "")
    assert num in [str(i) for i in range(1, 13)], f"Invalid column number: {num}"

    return f"{letter}:{num}"


# Build a dict to map a LIMS reagent label to its properties
ont_label2dict: dict[str, dict] = {}
for lims_kit, labels in lims_kits2labels.items():
    for label in labels:
        # Instantiate dict to store barcode properties
        label_dict: dict = {}
        label_dict["lims_kit"] = lims_kit
        label_dict["label"] = label
        label_dict["seq"] = label.split(" ")[-1][1:-1]
        label_dict["name"] = label.split("_")[-1].split(" ")[0]

        # Accommodate different format labels
        if lims_kit == "Nanopore native barcodes v2":
            # E.g. 01_A1_NB01 (CACAAAGACACCGACAACTTTCTT)
            label_dict["num"] = int(label[0:2].lstrip("0"))
            label_dict["well"] = format_well(label.split("_")[1])

        elif lims_kit == "EXP-PBC096":
            # E.g. A01_BC01 (AAGAAAGTTGTCGGTGTCTTTGTG)
            label_dict["num"] = int(label.split("_")[1].split(" ")[0][2:].lstrip("0"))
            label_dict["well"] = format_well(label.split("_")[0])
        else:
            raise NotImplementedError(f"Unknown kit(s): {lims_kit}")

        # Sanity check that the name/sequence-pairing of an ONT barcode is
        # the same in LIMS as in the ONT documentation.
        assert ont_name2seq[label_dict["name"]] == label_dict["seq"], (
            f"Barcode {label_dict['name']} sequence is mismatched between LIMS and ONT docs."
        )

        ont_label2dict[label] = label_dict
