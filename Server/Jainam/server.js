require("dotenv").config();
const express = require("express");
const axios = require("axios");
const crypto = require("crypto");
const { time } = require("console");

const app = express();
app.use(express.json());

const {
  APP_CODE,
  API_SECRET,
  REDIRECT_URL,
  PORT
} = process.env;

const sessions = {};
const now = new Date();

app.get("/login", (req, res) => {
  const loginUrl = `https://protrade.jainam.in/?appcode=${APP_CODE}`;
  res.redirect(loginUrl);
  console.log("/login", res.statusCode, now.toLocaleTimeString());
});

app.get("/", async (req, res) => {
  const { authCode, userId } = req.query;

  if (!authCode || !userId) {
    return res.status(400).send("Invalid SSO callback");
  }

  try {
    const checkSum = crypto
      .createHash("sha256")
      .update(userId + authCode + API_SECRET)
      .digest("hex");
    const response = await axios.post(
      "https://protrade.jainam.in/omt/auth/sso/vendor/getUserDetails",
      {
        userId,
        authCode,
        checkSum
      }
    );

    const accessToken = response.data.result[0].accessToken;

    sessions[userId] = {
      accessToken,
      createdAt: Date.now()
    };

    res.send(`
      <h2>Login Successful 🎉</h2>
      <p>User ID: ${userId}</p>
      <a href="/portfolio?userId=${userId}">View Portfolio</a>
    `).status(200);
  } catch (error) {
    console.error(error.response?.data || error.message);
    res.status(500).send("Failed to create user session");
  }
  console.log("/", res.statusCode, now.toLocaleTimeString());
});

app.get("/portfolio", async (req, res) => {
  const { userId } = req.query;

  if (!userId || !sessions[userId]) {
    return res.status(401).send("User not logged in");
  }

  const { accessToken } = sessions[userId];
  try {
    const portfolioResponse = await axios.get(
      "https://protrade.jainam.in/omt/api-order-rest/v1/holdings/productType",
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        }
      }
    );
    res.json({
      userId,
      portfolio: portfolioResponse.data
    }).status(200);
  } catch (error) {
    console.error(error.response?.data || error.message);
    res.status(500).send("Failed to fetch portfolio");
  }
  console.log("/portfolio", res.statusCode, now.toLocaleTimeString());
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on ${REDIRECT_URL}`);
});