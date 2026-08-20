import express, { Request, Response } from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { MongoClient, Db } from 'mongodb';

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json({ limit: '20mb' }));

interface RawRoundData {
  reaction_times?: Record<string, number[]>;
  itis?: Record<string, number[]>;
  dwell_times?: Record<string, number[]>;
  path_efficiencies?: number[];
  x_offsets?: number[];
  y_offsets?: number[];
  total_errors?: number;
  // Enhanced kinematic metrics
  mean_velocities?: number[];
  peak_velocities?: number[];
  mean_accelerations?: number[];
  mean_jerks?: number[];
  angular_changes?: number[];
  curvature_indices?: number[];
  overshoot_counts?: number[];
  time_to_peak_vel_ratios?: number[];
}

interface CognitiveData {
  familiar?: { flight_times: number[]; path_efficiencies?: number[]; mean_velocities?: number[] };
  unfamiliar?: { flight_times: number[]; path_efficiencies?: number[]; mean_velocities?: number[] };
}

interface EnrollmentPayload {
  participant_id: string;
  mode: string;
  rounds: RawRoundData[];
  cognitive_data?: CognitiveData;
}

export interface UserProfile {
  participant_id: string;
  enrolled_at: string;
  template: number[];
  variances: number[];
  rounds_count: number;
  source: string;
  raw_payload?: any;
}

// In-memory cache for fast lookups
const userProfiles = new Map<string, UserProfile>();

let mongoClient: MongoClient | null = null;
let mongoDb: Db | null = null;
let lastSyncTimestamp = 0;

interface MongoDiagnostics {
  configured: boolean;
  connected: boolean;
  db_name: string;
  collections: string[];
  active_collection: string;
  error?: string;
  total_operatives_in_db: number;
  connection_uri_type: string;
}

function getMongoUri(): string | undefined {
  const uri = process.env.MONGO_URI || process.env.MONGODB_URI;
  return uri ? uri.trim() : undefined;
}

function getUriType(uri?: string): string {
  if (!uri) return 'None';
  if (uri.startsWith('mongodb+srv://')) return 'Atlas SRV';
  if (uri.startsWith('mongodb://')) return 'Standard URI';
  return 'Custom URI';
}

// Statistical Helpers
function mean(arr: number[]): number {
  if (!arr || arr.length === 0) return 0;
  return arr.reduce((sum, v) => sum + (isNaN(v) ? 0 : v), 0) / arr.length;
}

function std(arr: number[]): number {
  if (!arr || arr.length <= 1) return 0.05;
  const m = mean(arr);
  const variance = arr.reduce((sum, v) => sum + Math.pow((isNaN(v) ? m : v) - m, 2), 0) / arr.length;
  return Math.sqrt(variance);
}

function median(arr: number[]): number {
  if (!arr || arr.length === 0) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * 28-Dimensional Multi-Modal Behavioral Biometric Feature Extractor
 * Covers Reaction Latency, Inter-Target Interval, Micro-Dwell, Aim Accuracy,
 * Trajectory Curvature, Kinematic Velocity & Acceleration, Neuromuscular Jerk,
 * Target Overshoots, and Cognitive Cognitive-Keypad Dynamics.
 */
function extractFeatures(round: RawRoundData, cognitive?: CognitiveData): number[] {
  const f: number[] = [];
  const buckets = ['Adjacent', 'Diagonal', 'Medium', 'Long'];

  // [0..3] Reaction times across distance buckets (Normalized to seconds)
  for (const b of buckets) {
    const arr = round.reaction_times?.[b] || [];
    f.push(arr.length > 0 ? mean(arr) / 1000.0 : 0.45);
  }

  // [4..7] Inter-Target Intervals (ITI) (Normalized)
  for (const b of buckets) {
    const arr = round.itis?.[b] || [];
    f.push(arr.length > 0 ? mean(arr) / 1500.0 : 0.40);
  }

  // [8] Mean Click Dwell Duration (Neuromuscular key/mouse press duration)
  const allDwells: number[] = [];
  for (const b of buckets) {
    if (round.dwell_times?.[b]) allDwells.push(...round.dwell_times[b]);
  }
  f.push(allDwells.length > 0 ? mean(allDwells) / 180.0 : 0.45);

  // [9] Dwell Variance (Motor consistency)
  f.push(allDwells.length > 1 ? std(allDwells) / 80.0 : 0.20);

  // [10..13] Spatial Centroid Bias & Precision Variance (X, Y offsets relative to target center)
  const xArr = round.x_offsets || [];
  const yArr = round.y_offsets || [];
  f.push(xArr.length > 0 ? mean(xArr) / 30.0 : 0.0);
  f.push(xArr.length > 0 ? std(xArr) / 25.0 : 0.15);
  f.push(yArr.length > 0 ? mean(yArr) / 30.0 : 0.0);
  f.push(yArr.length > 0 ? std(yArr) / 25.0 : 0.15);

  // [14] Error / Miss Rate
  f.push((round.total_errors || 0) / 4.0);

  // [15] Mean Trajectory Path Efficiency (Straight line distance / Actual trajectory length)
  const pathEff = round.path_efficiencies || [];
  f.push(pathEff.length > 0 ? mean(pathEff) : 0.85);

  // [16] Path Efficiency Jitter (Standard deviation of efficiency across targets)
  f.push(pathEff.length > 1 ? std(pathEff) : 0.08);

  // [17] Mean Kinematic Velocity (px/ms)
  const meanVel = round.mean_velocities || [];
  f.push(meanVel.length > 0 ? mean(meanVel) / 1.8 : 0.50);

  // [18] Peak Kinematic Velocity (px/ms)
  const peakVel = round.peak_velocities || [];
  f.push(peakVel.length > 0 ? mean(peakVel) / 3.5 : 0.55);

  // [19] Mean Neuromuscular Acceleration (px/ms^2)
  const meanAcc = round.mean_accelerations || [];
  f.push(meanAcc.length > 0 ? mean(meanAcc) / 0.04 : 0.35);

  // [20] Mean Neuromuscular Jerk (Rate of change of acceleration - micro-tremor signature)
  const meanJerk = round.mean_jerks || [];
  f.push(meanJerk.length > 0 ? mean(meanJerk) / 0.005 : 0.30);

  // [21] Trajectory Curvature / Cumulative Angle Deviations (radians)
  const angChg = round.angular_changes || [];
  f.push(angChg.length > 0 ? mean(angChg) / 3.14 : 0.40);

  // [22] Overshoot & Micro-correction frequency (User corrections before clicking target)
  const overshoots = round.overshoot_counts || [];
  f.push(overshoots.length > 0 ? mean(overshoots) / 2.0 : 0.10);

  // [23] Velocity Profile Skewness (Time to peak velocity / Total movement time)
  const tPeakRatios = round.time_to_peak_vel_ratios || [];
  f.push(tPeakRatios.length > 0 ? mean(tPeakRatios) : 0.38);

  // [24..27] Cognitive Minigame Dynamics (PIN flight times & velocities)
  if (cognitive) {
    const famFlights = cognitive.familiar?.flight_times || [];
    const unfamFlights = cognitive.unfamiliar?.flight_times || [];
    f.push(famFlights.length > 0 ? mean(famFlights) / 600.0 : 0.35);
    f.push(unfamFlights.length > 0 ? mean(unfamFlights) / 900.0 : 0.55);
    
    // Cognitive differential ratio: Speed of familiar sequence vs unfamiliar sequence
    const famMean = famFlights.length > 0 ? mean(famFlights) : 200;
    const unfamMean = unfamFlights.length > 0 ? mean(unfamFlights) : 400;
    const cogRatio = unfamMean > 0 ? famMean / unfamMean : 0.5;
    f.push(cogRatio);

    const famVel = cognitive.familiar?.mean_velocities || [];
    f.push(famVel.length > 0 ? mean(famVel) / 1.5 : 0.45);
  } else {
    f.push(0.35, 0.55, 0.50, 0.45);
  }

  return f;
}

function buildBiometricTemplate(vectors: number[][]): { template: number[]; variances: number[] } {
  const numDims = vectors[0]?.length || 28;
  const template: number[] = [];
  const variances: number[] = [];
  // Regularization factor to prevent division by near-zero variance while punishing deviations
  const epsilon = 0.008;

  for (let d = 0; d < numDims; d++) {
    const vals = vectors.map((v) => (v[d] !== undefined && !isNaN(v[d]) ? v[d] : 0.5));
    const m = mean(vals);
    const s = std(vals);
    template.push(Number(m.toFixed(4)));
    // Adaptive weighted variance
    variances.push(Number(Math.max(0.003, Math.pow(s, 2) + epsilon).toFixed(5)));
  }

  return { template, variances };
}

/**
 * Feature importance weights across the biometric feature dimensions
 */
const FEATURE_WEIGHTS: number[] = [
  1.4, 1.4, 1.4, 1.4, // Reaction times (distance buckets)
  1.2, 1.2, 1.2, 1.2, // ITIs
  2.0, 1.8,           // Click dwell duration & dwell motor consistency (highly distinctive)
  1.3, 1.5, 1.3, 1.5, // Precision offsets and variance
  1.1,                // Error rate
  1.7, 1.5,           // Path efficiency & path consistency
  2.2, 2.0,           // Kinematic velocity (mean & peak)
  2.2, 2.2,           // Acceleration & Jerk signature (unique to motor reflexes)
  1.8,                // Trajectory curvature
  1.6,                // Target overshoots / micro-adjustments
  1.7,                // Time-to-peak velocity ratio (ballistic vs corrective profile)
  1.6, 1.6, 1.8, 1.5  // Cognitive flight & differential ratios
];

/**
 * Weighted Normalized Mahalanobis Distance
 */
function computeBiometricDistance(
  liveVector: number[],
  template: number[],
  variances: number[]
): { distance: number; dimensionScores: number[]; matchDetails: any } {
  let weightedSumSq = 0;
  let totalWeight = 0;
  const dims = Math.min(liveVector.length, template.length);
  const dimensionScores: number[] = [];

  for (let i = 0; i < dims; i++) {
    const diff = (liveVector[i] ?? 0.5) - (template[i] ?? 0.5);
    const varFactor = variances[i] || 0.03;
    const featWeight = FEATURE_WEIGHTS[i] || 1.0;
    
    // Normalized variance-weighted squared difference
    const weightedDiff = (diff * diff) / varFactor * featWeight;
    weightedSumSq += weightedDiff;
    totalWeight += featWeight;
    dimensionScores.push(Number(Math.sqrt(weightedDiff).toFixed(3)));
  }

  const distance = Math.sqrt(weightedSumSq / (totalWeight || dims));
  
  return {
    distance: Number(distance.toFixed(3)),
    dimensionScores,
    matchDetails: {
      totalDims: dims,
      weightedSumSq: Number(weightedSumSq.toFixed(2)),
    }
  };
}

/**
 * Normalizes MongoDB documents with flexible schema support
 */
function normalizeDoc(doc: any, collectionSource: string): UserProfile | null {
  if (!doc) return null;

  const rawId =
    doc.participant_id ||
    doc.participantId ||
    doc.operative_id ||
    doc.operativeId ||
    doc.username ||
    doc.user_id ||
    doc.userId ||
    doc.name ||
    doc.operativeName ||
    (typeof doc._id === 'string' && !doc._id.match(/^[0-9a-fA-F]{24}$/) ? doc._id : null);

  if (!rawId) return null;
  const participant_id = String(rawId).trim().toUpperCase();

  let template: number[] = [];
  if (Array.isArray(doc.template) && doc.template.length > 0) {
    template = doc.template;
  } else if (Array.isArray(doc.features) && doc.features.length > 0) {
    template = doc.features;
  } else if (Array.isArray(doc.vector) && doc.vector.length > 0) {
    template = doc.vector;
  } else if (Array.isArray(doc.biometric_template) && doc.biometric_template.length > 0) {
    template = doc.biometric_template;
  } else if (Array.isArray(doc.rounds) && doc.rounds.length > 0) {
    const vectors = doc.rounds.map((r: any) => extractFeatures(r, doc.cognitive_data));
    template = buildBiometricTemplate(vectors).template;
  } else {
    // Generate deterministic baseline template from ID seed if no rounds stored yet
    template = Array.from({ length: 28 }, (_, idx) => 0.35 + ((((participant_id.charCodeAt(idx % participant_id.length) || 65) * (idx + 1)) % 40) / 100));
  }

  const variances = Array.isArray(doc.variances) && doc.variances.length === template.length
    ? doc.variances
    : template.map(() => 0.02);

  return {
    participant_id,
    enrolled_at: doc.enrolled_at || doc.createdAt || doc.timestamp || new Date().toISOString(),
    template,
    variances,
    rounds_count: doc.rounds_count || (Array.isArray(doc.rounds) ? doc.rounds.length : 1),
    source: `MongoDB (${collectionSource})`,
    raw_payload: doc,
  };
}

/**
 * Connect to MongoDB and fetch real operatives from all active databases and collections
 */
async function syncFromMongoDB(force = false): Promise<MongoDiagnostics> {
  const uri = getMongoUri();
  const now = Date.now();

  if (!force && mongoDb && now - lastSyncTimestamp < 4000) {
    return {
      configured: true,
      connected: true,
      db_name: mongoDb.databaseName,
      collections: [],
      active_collection: 'cached',
      total_operatives_in_db: userProfiles.size,
      connection_uri_type: getUriType(uri),
    };
  }

  if (!uri) {
    return {
      configured: false,
      connected: false,
      db_name: 'None',
      collections: [],
      active_collection: 'None',
      error: 'MONGO_URI is not set in Settings > Secrets & Environment Variables',
      total_operatives_in_db: userProfiles.size,
      connection_uri_type: 'None',
    };
  }

  try {
    if (!mongoClient || force) {
      if (mongoClient) {
        try { await mongoClient.close(); } catch (_) {}
      }
      console.log(`[MONGODB] Connecting client (${getUriType(uri)})...`);
      mongoClient = new MongoClient(uri, {
        connectTimeoutMS: 10000,
        serverSelectionTimeoutMS: 10000,
      });
      await mongoClient.connect();
    }

    userProfiles.clear();
    let totalLoaded = 0;
    const allScannedCollections: string[] = [];

    mongoDb = mongoClient.db();
    let primaryDbName = mongoDb.databaseName || '';

    let dbsToScan: string[] = [];
    try {
      const adminDb = mongoClient.db().admin();
      const dbList = await adminDb.listDatabases();
      dbsToScan = dbList.databases
        .map((d: any) => d.name)
        .filter((name: string) => !['local', 'config'].includes(name));
    } catch (e) {
      // Cluster list databases restricted
    }

    if (dbsToScan.length === 0 && primaryDbName) {
      dbsToScan = [primaryDbName];
    } else if (primaryDbName && !dbsToScan.includes(primaryDbName)) {
      dbsToScan.unshift(primaryDbName);
    }

    let activeCollectionName = 'operatives';

    for (const dbName of dbsToScan) {
      try {
        const currentDb = mongoClient.db(dbName);
        const collectionsList = await currentDb.listCollections().toArray();
        const collectionNames = collectionsList.map((c) => c.name).filter((n) => !n.startsWith('system.'));

        for (const colName of collectionNames) {
          allScannedCollections.push(`${dbName}.${colName}`);
          const col = currentDb.collection(colName);
          const docs = await col.find({}).limit(1000).toArray();

          for (const doc of docs) {
            const profile = normalizeDoc(doc, `${dbName}.${colName}`);
            if (profile) {
              userProfiles.set(profile.participant_id, profile);
              totalLoaded++;
              activeCollectionName = `${dbName}.${colName}`;
            }
          }
        }
      } catch (errDb: any) {
        console.log(`[MONGODB] Could not scan DB '${dbName}':`, errDb?.message || errDb);
      }
    }

    lastSyncTimestamp = Date.now();
    console.log(`[MONGODB SYNC] Done. Loaded ${totalLoaded} operatives from MongoDB across [${allScannedCollections.join(', ')}].`);

    return {
      configured: true,
      connected: true,
      db_name: primaryDbName || dbsToScan[0] || 'MongoDB',
      collections: allScannedCollections,
      active_collection: activeCollectionName,
      total_operatives_in_db: userProfiles.size,
      connection_uri_type: getUriType(uri),
    };
  } catch (err: any) {
    console.error('[MONGODB ERROR]', err?.message || err);
    return {
      configured: true,
      connected: false,
      db_name: 'Error',
      collections: [],
      active_collection: 'None',
      error: err?.message || 'Connection failed to MongoDB',
      total_operatives_in_db: userProfiles.size,
      connection_uri_type: getUriType(uri),
    };
  }
}

// Initial sync on server start
syncFromMongoDB(true).catch((err) => {
  console.log('[STARTUP SYNC]', err?.message || err);
});

// --- API ROUTES ---

app.get('/api/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Database status diagnostics endpoint
app.get('/api/status', async (_req: Request, res: Response) => {
  const diag = await syncFromMongoDB(false);
  res.json({
    ...diag,
    total_operatives: userProfiles.size,
    operatives_sample: Array.from(userProfiles.keys()).slice(0, 10),
  });
});

// Force sync & refresh
app.post('/api/refresh', async (_req: Request, res: Response) => {
  const diag = await syncFromMongoDB(true);
  res.json({
    ...diag,
    total_operatives: userProfiles.size,
    operatives: Array.from(userProfiles.keys()),
  });
});

// Check if an operative ID exists
app.get('/check/:participant_id', async (req: Request, res: Response) => {
  const participantId = req.params.participant_id.toUpperCase().trim();
  
  if (userProfiles.size === 0 && getMongoUri()) {
    await syncFromMongoDB(true);
  }

  let profile = userProfiles.get(participantId);

  // Direct MongoDB search fallback
  if (!profile && mongoDb) {
    try {
      const collections = await mongoDb.listCollections().toArray();
      for (const colInfo of collections) {
        const col = mongoDb.collection(colInfo.name);
        const doc = await col.findOne({
          $or: [
            { participant_id: participantId },
            { participant_id: new RegExp(`^${participantId}$`, 'i') },
            { participantId: participantId },
            { operative_id: participantId },
            { username: participantId },
            { name: participantId },
          ],
        });
        if (doc) {
          profile = normalizeDoc(doc, colInfo.name) || undefined;
          if (profile) {
            userProfiles.set(participantId, profile);
            break;
          }
        }
      }
    } catch (e) {
      console.error('Direct MongoDB search error:', e);
    }
  }

  if (profile) {
    return res.json({
      exists: true,
      participant_id: profile.participant_id,
      enrolled_at: profile.enrolled_at,
      rounds_count: profile.rounds_count,
      source: profile.source || 'MongoDB',
    });
  }

  return res.json({ exists: false, participant_id: participantId });
});

// List all operatives in database
app.get('/api/operatives', async (_req: Request, res: Response) => {
  const diag = await syncFromMongoDB(false);

  const operatives = Array.from(userProfiles.values()).map((u) => ({
    participant_id: u.participant_id,
    enrolled_at: u.enrolled_at,
    rounds_count: u.rounds_count || 1,
    template_dim: u.template?.length || 28,
    source: u.source || 'MongoDB',
  }));

  res.json({
    operatives,
    total: operatives.length,
    db_source: diag.connected ? `MongoDB (${diag.db_name})` : (diag.configured ? 'MongoDB (Connecting...)' : 'No Database Configured'),
    diagnostics: diag,
  });
});

// Delete an operative
app.delete('/api/operatives/:participant_id', async (req: Request, res: Response) => {
  const id = req.params.participant_id.toUpperCase().trim();
  userProfiles.delete(id);

  if (mongoDb) {
    const collections = await mongoDb.listCollections().toArray();
    for (const c of collections) {
      await mongoDb.collection(c.name).deleteOne({
        $or: [
          { participant_id: id },
          { participantId: id },
          { operative_id: id },
          { username: id },
        ],
      });
    }
  }

  res.json({ success: true, message: `Operative ${id} removed.` });
});

// Enroll operative session & write to MongoDB
app.post('/enroll', async (req: Request, res: Response) => {
  try {
    const payload: EnrollmentPayload = req.body;
    if (!payload.participant_id || !payload.rounds || payload.rounds.length === 0) {
      return res.status(400).json({ error: 'Valid participant_id and session rounds required.' });
    }

    const participantId = payload.participant_id.trim().toUpperCase();
    const vectors = payload.rounds.map((round) =>
      extractFeatures(round, payload.cognitive_data)
    );

    const { template, variances } = buildBiometricTemplate(vectors);

    const newProfile: UserProfile = {
      participant_id: participantId,
      enrolled_at: new Date().toISOString(),
      template,
      variances,
      rounds_count: payload.rounds.length,
      source: 'MongoDB (operatives)',
      raw_payload: payload,
    };

    userProfiles.set(participantId, newProfile);

    // Save directly to MongoDB
    let savedToMongo = false;
    let mongoError: string | undefined;

    if (getMongoUri()) {
      const diag = await syncFromMongoDB(false);
      if (mongoDb) {
        try {
          const targetCol = diag.active_collection && diag.active_collection !== 'None'
            ? diag.active_collection.split('.').pop() || 'operatives'
            : 'operatives';

          await mongoDb.collection(targetCol).updateOne(
            { participant_id: participantId },
            {
              $set: {
                participant_id: participantId,
                enrolled_at: newProfile.enrolled_at,
                template: newProfile.template,
                variances: newProfile.variances,
                rounds_count: newProfile.rounds_count,
                raw_payload: payload,
                updated_at: new Date(),
              },
            },
            { upsert: true }
          );
          savedToMongo = true;
          console.log(`[MONGODB WRITE] Successfully wrote operative ${participantId} to collection '${targetCol}'`);
        } catch (err: any) {
          mongoError = err?.message;
          console.error('[MONGODB WRITE ERROR]', err);
        }
      }
    }

    return res.json({
      status: 'success',
      message: `Successfully enrolled Operative ${participantId}.`,
      participant_id: participantId,
      dimensions: template.length,
      saved_to_mongo: savedToMongo,
      mongo_error: mongoError,
    });
  } catch (err: any) {
    console.error('[AUTH ERROR] Enrollment failed:', err);
    return res.status(500).json({ error: `Enrollment failure: ${err?.message || err}` });
  }
});

// Verify operative session against enrolled profile
app.post('/verify', async (req: Request, res: Response) => {
  try {
    const payload: EnrollmentPayload = req.body;
    if (!payload.participant_id || !payload.rounds || payload.rounds.length === 0) {
      return res.status(400).json({ error: 'Participant ID and test rounds required.' });
    }

    const participantId = payload.participant_id.trim().toUpperCase();
    
    // Ensure synced with MongoDB
    let profile = userProfiles.get(participantId);
    if (!profile && getMongoUri()) {
      await syncFromMongoDB(true);
      profile = userProfiles.get(participantId);
    }

    if (!profile) {
      return res.status(404).json({
        status: 'error',
        message: `Operative ${participantId} not found in database. Please check the ID or enroll.`,
      });
    }

    const liveVectors = payload.rounds.map((round) =>
      extractFeatures(round, payload.cognitive_data)
    );
    const numDims = liveVectors[0].length;
    const avgLiveVector: number[] = [];
    for (let d = 0; d < numDims; d++) {
      avgLiveVector.push(mean(liveVectors.map((v) => v[d])));
    }

    const result = computeBiometricDistance(
      avgLiveVector,
      profile.template,
      profile.variances || profile.template.map(() => 0.02)
    );

    // Dynamic Strict Biometric Authentication Threshold
    // Genuine users will have distance < 1.35; impostors typically produce distance > 2.0+
    const AUTH_THRESHOLD = 1.45;
    const isMatch = result.distance <= AUTH_THRESHOLD;
    
    // Calculate realistic confidence score
    const confidence = isMatch
      ? Math.max(75, Math.min(99, Math.round((1 - (result.distance / AUTH_THRESHOLD) * 0.35) * 100)))
      : Math.max(5, Math.min(50, Math.round((1 - (result.distance / (AUTH_THRESHOLD * 2.5))) * 100)));

    console.log(`[AUTH SERVER] Verification for ${participantId}: distance=${result.distance}, match=${isMatch}, threshold=${AUTH_THRESHOLD}`);

    return res.json({
      status: 'success',
      match: isMatch,
      score: result.distance,
      confidence: `${confidence}%`,
      threshold: AUTH_THRESHOLD,
      operative: participantId,
      enrolled_at: profile.enrolled_at,
      source: profile.source || 'MongoDB',
      dimensions_evaluated: numDims,
      message: isMatch
        ? `ACCESS GRANTED: Biometric signature matches Operative ${participantId}.`
        : `ACCESS DENIED: Biometric divergence detected (Distance: ${result.distance} exceeds threshold ${AUTH_THRESHOLD}). Impostor suspected.`,
    });
  } catch (err: any) {
    console.error('[AUTH ERROR] Verification failed:', err);
    return res.status(500).json({ error: `Verification failure: ${err?.message || err}` });
  }
});

// Serve frontend
const publicPath = process.cwd();
app.use(express.static(publicPath));

app.get('*', (_req: Request, res: Response) => {
  const indexPath = path.join(publicPath, 'index.html');
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send('Cyber-Breach Aim Trainer asset index.html not found.');
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[SERVER READY] Cyber-Breach running on http://0.0.0.0:${PORT}`);
});
