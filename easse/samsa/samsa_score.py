from typing import List

from easse.samsa.ucca_utils import get_scenes, ucca_parse_text
from easse.aligner.aligner import align
import easse.utils.preprocessing as utils_prep


def align_scenes_sentences(scenes, sentences):
    all_scenes_alignments = []
    for scene in scenes:
        scene_alignments = []
        for sentence in sentences:
            # word_alignments = [[word1_scene, word1_sentence], [word2_scene, word3_sentence], ...]
            word_alignments = align(scene, sentence)[1]
            scene_alignments.append(word_alignments)
        all_scenes_alignments.append(scene_alignments)
    return all_scenes_alignments


def get_num_scenes(ucca_passage):
    """
    Returns the number of scenes in the ucca_passage.
    """
    scenes = [x for x in ucca_passage.layer("1").all if x.tag == "FN" and x.is_scene()]
    return len(scenes)


def get_relations_minimal_centers(ucca_passage):
    """
    Return all the most internal centers of main relations in each passage
    """
    scenes = [x for x in ucca_passage.layer("1").all if x.tag == "FN" and x.is_scene()]
    minimal_centers = []
    for sc in scenes:
        mrelations = [e.child for e in sc.outgoing if e.tag == 'ucca_passage' or e.tag == 'S']
        for mr in mrelations:
            centers = [e.child for e in mr.outgoing if e.tag == 'C']
            if centers:
                while centers:
                    for c in centers:
                        ccenters = [e.child for e in c.outgoing if e.tag == 'C']
                    lcenters = centers
                    centers = ccenters
                minimal_centers.append(lcenters)
            else:
                minimal_centers.append(mrelations)

    y = ucca_passage.layer("0")
    output = []
    for scp in minimal_centers:
        for par in scp:
            output2 = []
            positions = [d.position for d in par.get_terminals(False, True)]
            for pos in positions:
                if not output2:
                    output2.append(str(y.by_position(pos)))
                elif str(y.by_position(pos)) != output2[-1]:
                    output2.append(str(y.by_position(pos)))

        output.append(output2)

    return output


def get_participants_minimal_centers(P):
    """
    P is a ucca passage. Return all the minimal participant centers in each scene
    """
    scenes = [x for x in P.layer("1").all if x.tag == "FN" and x.is_scene()]
    n = []
    for sc in scenes:  # find participant nodes
        m = []
        participants = [e.child for e in sc.outgoing if e.tag == 'A']
        for pa in participants:
            centers = [e.child for e in pa.outgoing if e.tag == 'C']
            if centers != []:
                while centers != []:
                    for c in centers:
                        ccenters = [e.child for e in c.outgoing if e.tag == 'C' or e.tag == 'P' or e.tag == 'S']   #also addresses center Scenes
                    lcenters = centers
                    centers = ccenters
                m.append(lcenters)
            elif pa.is_scene():  # address the case of Participant Scenes
                scenters = [e.child for e in pa.outgoing if e.tag == 'P' or e.tag == 'S']
                for scc in scenters:
                    centers = [e.child for e in scc.outgoing if e.tag == 'C']
                    if centers != []:
                        while centers != []:
                            for c in centers:
                                ccenters = [e.child for e in c.outgoing if e.tag == 'C']
                            lcenters = centers
                            centers = ccenters
                        m.append(lcenters)
                    else:
                        m.append(scenters)
            elif any(e.tag == "H" for e in pa.outgoing):  # address the case of multiple parallel Scenes inside a participant
                hscenes = [e.child for e in pa.outgoing if e.tag == 'H']
                mh = []
                for h in hscenes:
                    hrelations = [e.child for e in h.outgoing if e.tag == 'P' or e.tag == 'S']  # in case of multiple parallel scenes we generate new multiple centers
                    for hr in hrelations:
                        centers = [e.child for e in hr.outgoing if e.tag == 'C']
                        if centers != []:
                            while centers != []:
                                for c in centers:
                                    ccenters = [e.child for e in c.outgoing if e.tag == 'C']
                                lcenters = centers
                                centers = ccenters
                            mh.append(lcenters[0])
                        else:
                            mh.append(hrelations[0])
                m.append(mh)
            else:
                m.append([pa])

        n.append(m)

    y = P.layer("0")  # find cases of multiple centers
    output = []
    s = []
    I = []
    for scp in n:
        r = []
        u = n.index(scp)
        for par in scp:
            if len(par) > 1:
                d = scp.index(par)
                par = [par[i:i+1] for i in range(len(par))]
                for c in par:
                    r.append(c)
                I.append([u,d])
            else:
                r.append(par)
        s.append(r)

    for scp in s:  # find the spans of the participant nodes
        output1 = []
        for [par] in scp:
            output2 = []
            p = []
            d = par.get_terminals(False,True)
            for i in range(0, len(d)):
                p.append(d[i].position)

            for k in p:

                if(len(output2)) == 0:
                    output2.append(str(y.by_position(k)))
                elif str(y.by_position(k)) != output2[-1]:
                    output2.append(str(y.by_position(k)))
            output1.append(output2)
        output.append(output1)

    y = []  # unify spans in case of multiple centers
    for scp in output:
        x = []
        u = output.index(scp)
        for par in scp:
            for v in I:
                if par == output[v[0]][v[1]]:
                    for l in range(1,len(n[v[0]][v[1]])):
                        par.append((output[v[0]][v[1]+l])[0])

                    x.append(par)
                elif all(par != output[v[0]][v[1]+l] for l in range(1, len(n[v[0]][v[1]]))):
                    x.append(par)
            if not I:
                x.append(par)
        y.append(x)

    return y


def compute_samsa(orig_sentence, sys_sentences):
    orig_ucca_passage = ucca_parse_text(orig_sentence)
    orig_scenes = get_scenes(orig_ucca_passage)

    all_scenes_alignments = align_scenes_sentences(orig_scenes, sys_sentences)

    orig_num_scenes = get_num_scenes(orig_ucca_passage)  # len(orig_scenes)
    sys_num_sents = len(sys_sentences)

    M1 = get_relations_minimal_centers(orig_ucca_passage)
    A1 = get_participants_minimal_centers(orig_ucca_passage)

    if orig_num_scenes < sys_num_sents:
        score = 0.0
    elif orig_num_scenes == sys_num_sents:
        t = all_scenes_alignments
        match = []
        for i in range(orig_num_scenes):
            match_value = 0
            for j in range(sys_num_sents):
                if len(t[i][j]) > match_value and j not in match:
                    match_value = len(t[i][j])
                    m = j
            match.append(m)

        scorem = []
        scorea = []
        for i in range(orig_num_scenes):
            j = match[i]
            r = [t[i][j][k][0] for k in range(len(t[i][j]))]
            if not M1[i]:
                s = 0.5
            elif all(M1[i][l] in r for l in range(len(M1[i]))):
                s = 1
            else:
                s = 0
            scorem.append(s)
            sa = []
            if not A1[i]:
                sa = [0.5]
                scorea.append(sa)
            else:
                for a in A1[i]:
                    if not a:
                        p = 0.5
                    elif all(a[l] in r for l in range(len(a))):
                        p = 1
                    else:
                        p = 0
                    sa.append(p)
                scorea.append(sa)

        scoresc = []
        for i in range(orig_num_scenes):
            d = len(scorea[i])
            v = 0.5*scorem[i] + 0.5*(1/d)*sum(scorea[i])
            scoresc.append(v)
        score = (sys_num_sents/(orig_num_scenes**2))*sum(scoresc)
    else:
        t = all_scenes_alignments
        match = []
        for i in range(orig_num_scenes):
            match_value = 0
            for j in range(sys_num_sents):
                if len(t[i][j]) > match_value:
                    match_value = len(t[i][j])
                    m = j
            match.append(m)

        scorem = []
        scorea = []
        for i in range(orig_num_scenes):
            j = match[i]
            r = [t[i][j][k][0] for k in range(len(t[i][j]))]
            if not M1[i]:
                s = 0.5
            elif all(M1[i][l] in r for l in range(len(M1[i]))):
                s = 1
            else:
                s = 0
            scorem.append(s)
            sa = []
            if not A1[i]:
                sa = [0.5]
                scorea.append(sa)
            else:
                for a in A1[i]:
                    if not a:
                        p = 0.5
                    elif all(a[l] in r for l in range(len(a))):
                        p = 1
                    else:
                        p = 0
                    sa.append(p)
                scorea.append(sa)

        scoresc = []
        for i in range(orig_num_scenes):
            d = len(scorea[i])
            v = 0.5*scorem[i] + 0.5*(1/d)*sum(scorea[i])
            scoresc.append(v)
        score = (sys_num_sents/(orig_num_scenes**2))*sum(scoresc)
    return score


def samsa_corpus(orig_sentences: List[str], sys_outputs: List[str], lowercase: bool = False, tokenizer: str = '13a'):

    orig_sentences = [utils_prep.normalize(sent, lowercase, tokenizer) for sent in orig_sentences]
    sys_sentences = [utils_prep.split_into_sentences(utils_prep.normalize(output, lowercase, tokenizer))
                     for output in sys_outputs]

    samsa_score = 0.0
    for orig_sent, sys_sents in zip(orig_sentences, sys_sentences):
        samsa_score += compute_samsa(orig_sent, sys_sents)

    samsa_score /= len(orig_sentences)

    return samsa_score