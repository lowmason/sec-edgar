# Task 8 fresh Spec/Quality review — controller retained operative receipt

Reviewer: /root/task8_review, fresh gpt-6.1-sol / max / fork none. Named task-reviewer role unavailable; default role used with Full Form contract. Range 73ea758e37f6b6ed78103b2a731b2f125bd96a96..a62c05c0a961fecc2f1ac854b9dac68be3add7ef. Source/docs frozen throughout. This retains every operative finding, verdict, verification result and scope gap from the final reviewer message; strengths and descriptive verification prose are condensed. Exact independent probe source/command/output retained in task-8-review-guard-probe/. No new probe executed by controller.

**Spec Compliance: FAIL. Task Quality: NEEDS_FIXES.** Missing required combined Step4 proof, incomplete Step3 network/auth guard, missing Step5 installation instructions. Independent acquisition/result implementation, recovery/process evidence, artifacts and current checks otherwise satisfy assessed requirements. Whole-branch review remains separate. Critical: none. Minor: none additional.

## Important I1 — Missing required combined Step4 gate (owner NEEDS_CONTEXT)

fixture-sequence.py:112 deliberately expects daily exit2 under closed2015Q1. Alternative at:120 unexecuted; sec-edgar-stage-2-ajod3d_r/sequence-summary.json:10 honestly pending. Exact endpoint refusal is correct, but required single retained sequence must cover archivedquarter, handoff daily, delayedpending/recovery/stablepins/no new requests for completedmembers. Independentquarterly/ordinaryopendaily do not dischargegate. Obtain concrete ownerendpointdecision, execute approved combinedsequence, retain argv/exits/state/hashes/rootmap/summary. Do not relax productionpin/hashvalidators to forceconflictingexample. Task8/Stage2 cannot complete pending thisgate.

## Important I2 — Missing Step3 test network/auth protection

packages/sec-edgar-ingest/tests/support.py:1297 patches only socket.socket.connect, permits every127.0.0.1/::1port, has no authenticationdenialhook. Only calls: CLI subprocesswrapper:1312 andresultcrashwrapper:1462. scripts/check-sec-edgar-ingest.sh:3 ordinaryunittestdiscovery has no suiteguard. Focusedsupport/callsiteinspection found no suite-wideguard.

Exact bounded offlineprobe replaces both underlyingconnectionmethods with recordingstubs; no network/auth attempted. Importingsupport leaves connectunchanged. Explicithelper rejects nonloopbackconnect, permits arbitrary127.0.0.1:54321, leaves connect_ex reaching originalrecordingstub for198.51.100.1:443. Auth omission grounded in helper/runner source; unchangedcredentialclassidentity is NOT complete constructor/tokenbehaviorproof. Scopedfixture sender/no livefallback andexistingselected-origin loopbacksender are sound but do not satisfy suite-support requirement.

Requiredfix: install fixture-only denial before suiteexecution and relevantspawnedprocesses, cover connection/resolutionpaths, deny unapprovedauthenticationactivity, permit onlyexplicitlyselected boundedloopbackorigins. FocusedbehavioralRED/GREEN usingstubs. ProductionCLI outsideguard. Originalprobe /private/tmp/sec-task8-review-guard-96ho7hbw/{probe.py,receipt.json,stdout.txt}; exactcopies/hash/rootmap in task-8-review-guard-probe/.

## Important I3 — Missing Step5 explicit installation instructions

packages/sec-edgar-ingest/README.md:9 hasbuild/run/check, :18 describespins. docs/runbooks/sec-edgar-ingest-acquisition.md:3 assumesinstalledcommand/workspaceentrypoint andgivesfixtureinvocations. NeitherREADME/runbook gives promisedexactinstallinvocation. Addexplicitofflineinstall/setuprecipe with cachedprerequisites/pinnedwheelinstallation. Validated export/install commands in verification/installed-wheel-proof.py:94 are concretebasis. Preserve prohibitionon quietlyfetchingmissingdeps/changingpins.

## Verified strengths and checks (condensed from reviewer)

- Read complete3127-line42-path authoredview sequentially; everyowned deliverable hascorrespondinghunk. Fullstandarddiff4851paths:4815verification+36outside. NecessarydownloadFixturePack/modelsresultcodec/supportbuilders/test_workspacestaleassertions extensions; no unrelatedfeatures. Exactrequestedcommittitle. Nooriginalfourdeletions/localroadmap incommit.
- cli.py:80 prebackendvalidation, :135/:148 savedcontext/frozenintent refusechangedcorrelation/config/versions/deadline/manifest/inputs. test_cli.py:106 actualseparateparserprocesses. Currentcollectcontext versusfrozenupstreamorigin correct.
- results.py:33 exactbegunAttempt/conflictingcompletion/canonicalimmutableobject beforefinishAttempt; canonicalreader/pathcorrelation. test_cli.py:244 fourACTUALresult/Attemptcrashes74->0/originalcontext/repair/noadditionaltransport. Task7returnhook isnottheseproofs.
- download.py:687 strictmanifest/provenance/canonicalSECURLs/safebodies/hashes/faultshape/conditionalfixturecursor/missingexhaustedfailclosed. Pack10URLs/11responses/fullZIPoneDEFLATEmaster.idx/dailypreviousquarterempty/delayed404->200; allbodyhashes/lengthsmatch.
- test_acquisition_processes.py:17 andfinalthreecollectortrace:530 threePIDs/threeabsentreads/threeactualinserts/onewinner/twoconflicts/commonpin/noHTTPrestart; peakactive1/no unmatchedends, spacings0.673325917/0.670329s, rawbyteshashverified.
- test_acquisition_processes.py:71 +finalintegratedtakeovertrace:2997 actualheldsocket,parent-15/persistedguard/92zeros/socketdrain/dailybackfill0. FirstsuccessorafterguardANDsocketclosure, daily/daily/daily/backfill/minspacing0.680565s. Fatalchildtrace:4 actual-14/98prefixbytesverifiedSHA, stale0serverevents. Syntheticshortbounds/productiondefaults intact; nofull90/Linuxclaim.
- installed-wheel-proof.py:94 freshenv20cachedpins/frozenhashes/no-depwheel/importsite-packages/actualinstalledcommands0/fourtransportrowsunchanged. Metadata>=3.14/fourdirectpins/entrypoint/sourceexclusions correct. All18currentPythonfiles equalwheel. WheelSHA46deb58c54bb35cc79283f03ebf9ae4060ba23b2af5bbb8856ab0308c4913bb0;sdistSHAdac15ddd67184480a9df0810d4e41a0a6c181c24e64608451a2156af36b3643d.
- Independent4813payloadfiles/22181542bytes +4675mappedhistoryfiles allhashmatch; everyevidencepath indiff. inventory:18 correct/topmanifestSHA89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926. Postcheckpointcontrollerprogressappend doesnot invalidateunchangedrecordedcheckpoint. Historicfails honestlyretained.
- Completefinalchecklog:289 307lines/282passingrecords/no warning/unexpectednontestoutput/builds/help/version/exit0/47241bytes/SHA6387624674edb1a6f0dcfd68d4e8f0751344e51d58aa1a29db40d0ff5189090f. No suitererun. InitialCLIRE D14tests18fail5errors/processmissingbuilders/spawnevent/oldprocess-greenexit1 correctly distinguishedfromlaterfocused/currentPASS.
- Concreteunchangedriskchecks: pin_context savedstart/exactpins, state exactconditionalbegin/finish, collect currentcontext/gaps/halt/sourceinput, SenderFailure inheritsOwnershipLost, CollectionRaceStoreactualinsertdelegation, selectedoriginloopbackvalidation. No broadcrawl/newsubagents/livework. Probe only recordingstubs.
- Primarypreservationreceipt:6 exit0/no protecteddrift/no restoreddeletions/original4+untrackedroadmap; execution/config/lockhashesseparate.

## Cannot verify / remaining gates

FullupstreamAzure independentreleaseguard, ownerwidepolicyblock,promotionreceiptAuthorization,olderrevisit/allcodecstorageinvariants not reaudited taskscoped; priorreview/regressionrecords supportthem, controllercross-taskclosure/finalwholebranchreview required. ActualeffectiveAzurelease/inflight/CAS/HNS/identitynetwork/workermeasurement/Linux/default90/live smoke/replay remainunverified andALL22S7reservedincluding11/12/14/18/19. Pendingownerdecision/approvedcombinedsequence/fixreceipts/appendonlycontrollerreviewcheckpoint/finalwholebranch/Stage2stamp tickretirement stillrequired. No technicalevidencewaivesthem.

Controller adjudication: adopt I2/I3 for one same-implementer fix round with behavioral RED/GREEN and prescribed current checks; I1 remains genuinely missing owner context, not an authorized validator change. No Minor deferral. Task8 not complete.
